# -*- coding: utf-8 -*-
"""작물 분류 딥러닝 모델의 아키텍처와 전처리.

학습(train_crop_model.py)과 추론(vision.py)이 절대 어긋나면 안 되므로
두 군데서 쓰는 아키텍처·전처리를 여기 한 곳에만 둔다.

[중요] 이 파일은 vision.py 안에서 지연 임포트(함수 내부 import)로만 쓴다.
       torch가 없는 환경에서도 vision.py 자체는 정상적으로 import 되어야 한다.
"""

import cv2
import torch
from torch import nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

IMG_SIZE = 224
EMBED_DIM = 576   # mobilenet_v3_small의 avgpool 이후 차원


def build_backbone(pretrained):
    """특징 추출용 백본. features + avgpool까지만 쓰고 분류기(classifier)는 버린다.

    pretrained=True  학습 때: ImageNet 사전학습 가중치를 내려받는다 (인터넷 필요).
    pretrained=False 추론 때: 빈 뼈대만 만든다. 실제 값은 저장된 state_dict로 채운다
                      (대회장에 인터넷이 없어도 동작해야 하므로).
    """
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    net = mobilenet_v3_small(weights=weights)
    return net.features, net.avgpool


class CropClassifier(nn.Module):
    """얼린 백본 + 학습되는 선형 헤드. state_dict() 전체(백본+헤드)를 그대로 저장/로드한다."""

    def __init__(self, num_classes, pretrained=False):
        super().__init__()
        self.features, self.avgpool = build_backbone(pretrained)
        for p in self.features.parameters():
            p.requires_grad = False
        self.head = nn.Linear(EMBED_DIM, num_classes)

    def embed(self, x):
        """백본을 통과시켜 (N, 576) 임베딩만 뽑는다. 학습 때 캐싱용."""
        with torch.no_grad():
            x = self.features(x)
            x = self.avgpool(x)
            x = torch.flatten(x, 1)
        return x

    def forward(self, x):
        return self.head(self.embed(x))


def build_model(num_classes, pretrained=False):
    return CropClassifier(num_classes, pretrained=pretrained)


# ImageNet 정규화 상수 (사전학습 가중치와 반드시 짝을 맞춰야 한다)
_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def preprocess(bgr_crop):
    """CROP_ROI로 이미 잘라낸 BGR ndarray -> (1, 3, 224, 224) 정규화 텐서."""
    rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
    tensor = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
    tensor = (tensor - _MEAN) / _STD
    return tensor.unsqueeze(0)
