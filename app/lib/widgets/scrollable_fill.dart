import 'package:flutter/material.dart';

/// 실제 기기는 화면 높이가 제각각이다(작은 폰 ~ 큰 폰).
/// 화면이 넉넉하면 [child]가 세로로 가운데 정렬되고(child의 mainAxisAlignment로
/// 조절), 화면이 짧아서 내용이 다 안 들어가면 잘리는 대신 스크롤된다.
class ScrollableFill extends StatelessWidget {
  const ScrollableFill({super.key, required this.child, this.padding = EdgeInsets.zero});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        padding: padding,
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: child,
        ),
      ),
    );
  }
}
