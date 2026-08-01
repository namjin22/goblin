# -*- coding: utf-8 -*-
"""작물 분류 모델 학습.

data/<클래스이름>/*.jpg 를 모아서 학습한다.
백본(mobilenet_v3_small)은 얼려두고, 이미지당 임베딩을 한 번만 뽑아 캐싱한 뒤
그 위에 선형 분류기(nn.Linear)만 학습한다. 매 epoch 백본을 다시 통과시키는
일반적인 fine-tuning보다 훨씬 빠르고, 데이터가 적을 때 과적합도 덜하다.

사용법
  python train_crop_model.py

결과물
  models/crop_classifier.pt   학습된 모델 전체(백본+헤드)의 state_dict
  models/class_map.json       분류기 출력 인덱스 -> 클래스 이름 매핑
"""

import json
import os
import random

import cv2
import numpy as np
import torch
from torch import nn

from crop_model import build_model, preprocess
from profiles import CROP_PROFILES

DATA_DIR = "data"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "crop_classifier.pt")
CLASS_MAP_PATH = os.path.join(MODEL_DIR, "class_map.json")

VAL_RATIO = 0.2
EPOCHS = 150
LR = 1e-2
SEED = 42


def discover_classes():
    """data/ 아래 실제로 사진이 있는 클래스 폴더만 찾는다.

    profiles.py의 작물 키 + background 만 유효한 클래스로 인정한다.
    (엉뚱한 폴더가 섞여 있어도 무시)
    """
    valid = set(CROP_PROFILES.keys()) | {"background"}
    if not os.path.isdir(DATA_DIR):
        return []
    classes = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if name not in valid or not os.path.isdir(path):
            continue
        images = [f for f in os.listdir(path) if f.lower().endswith(".jpg")]
        if images:
            classes.append(name)
    return classes


def augment(img):
    """오프라인 증강: 좌우반전 + 밝기 + 회전 + 확대(줌).

    [배경] 15장짜리 원본 사진으로 학습한 모델이 원본 사진과 똑같이 찍으면
    100% 맞히는데(실제 확인함), 실물 카메라 - 브릭 개수가 많아지거나
    조명이 조금만 달라도 엉뚱한 클래스로 쏠리는 문제가 있었다. 원본과
    조건이 100% 같을 때만 잘 맞히는 건 과적합 신호라, 학습 때부터 더
    다양한 조건(밝기 범위 확대, 회전, 확대/축소)을 흉내 내서 조금 달라진
    실물 조건에도 버틸 수 있게 한다.
    """
    variants = [img, cv2.flip(img, 1)]

    for factor in (0.7, 0.85, 1.15, 1.3):
        bright = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
        variants.append(bright)

    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)

    for angle in (-15, 15):
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
        variants.append(rotated)

    # 확대(zoom in) - 브릭이 늘어서 화면을 더 채우는 실물 상황을 흉내낸다.
    for scale in (1.15, 1.3):
        matrix = cv2.getRotationMatrix2D(center, 0, scale)
        zoomed = cv2.warpAffine(img, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
        variants.append(zoomed)

    return variants


def load_embeddings(model, classes):
    """모든 이미지를 증강 -> 전처리 -> 임베딩 캐싱. (X, y) 반환."""
    X, y = [], []
    for label_idx, name in enumerate(classes):
        class_dir = os.path.join(DATA_DIR, name)
        files = [f for f in os.listdir(class_dir) if f.lower().endswith(".jpg")]
        n_variants = None
        for fname in files:
            img = cv2.imread(os.path.join(class_dir, fname))
            if img is None:
                continue
            variants = augment(img)
            n_variants = len(variants)
            for variant in variants:
                tensor = preprocess(variant)
                emb = model.embed(tensor)
                X.append(emb.squeeze(0))
                y.append(label_idx)
        print("  %-12s %3d장 원본 -> %3d장 (증강 포함, %d배)"
              % (name, len(files), len(files) * (n_variants or 0), n_variants or 0))
    return torch.stack(X), torch.tensor(y, dtype=torch.long)


def stratified_split(y, val_ratio, seed):
    """클래스별로 val_ratio만큼 검증셋 인덱스를 뽑는다."""
    rng = random.Random(seed)
    train_idx, val_idx = [], []
    for label in sorted(set(y.tolist())):
        idxs = [i for i, v in enumerate(y.tolist()) if v == label]
        rng.shuffle(idxs)
        n_val = max(1, int(len(idxs) * val_ratio))
        val_idx += idxs[:n_val]
        train_idx += idxs[n_val:]
    return train_idx, val_idx


def main():
    classes = discover_classes()
    if len(classes) < 2:
        print("data/ 아래 학습 가능한 클래스가 2개 미만이다.")
        print("python collect_data.py --crop <이름> 으로 먼저 사진을 찍을 것.")
        return 1

    print("학습 클래스 (%d개): %s" % (len(classes), ", ".join(classes)))

    torch.manual_seed(SEED)
    model = build_model(len(classes), pretrained=True)
    model.eval()

    print("\n임베딩 캐싱 중...")
    X, y = load_embeddings(model, classes)
    print("총 %d개 임베딩 (증강 포함)" % len(X))

    train_idx, val_idx = stratified_split(y, VAL_RATIO, SEED)
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print("학습 %d개 / 검증 %d개" % (len(X_train), len(X_val)))

    # weight_decay(L2 정규화) - 데이터가 적을 때 선형 헤드가 몇몇 픽셀
    # 패턴에 과도하게 의존하는 걸 눌러준다. 실물에서 조건이 살짝 달라져도
    # 더 안정적으로 버티게 하려는 목적.
    optimizer = torch.optim.Adam(model.head.parameters(), lr=LR, weight_decay=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    print("\n선형 헤드 학습 중...")
    for epoch in range(EPOCHS):
        model.head.train()
        optimizer.zero_grad()
        logits = model.head(X_train)
        loss = loss_fn(logits, y_train)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 30 == 0 or epoch == EPOCHS - 1:
            model.head.eval()
            with torch.no_grad():
                val_acc = (model.head(X_val).argmax(1) == y_val).float().mean().item()
            print("  epoch %3d  loss %.4f  val_acc %.1f%%"
                  % (epoch + 1, loss.item(), val_acc * 100))

    model.head.eval()
    with torch.no_grad():
        final_acc = (model.head(X_val).argmax(1) == y_val).float().mean().item()

    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    with open(CLASS_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(classes, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(" 최종 검증 정확도: %.1f%%" % (final_acc * 100))
    print(" 저장 완료: %s, %s" % (MODEL_PATH, CLASS_MAP_PATH))
    if final_acc < 0.85:
        print(" [주의] 정확도가 낮다. 사진을 더 찍거나 다양한 각도로 다시 찍을 것.")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
