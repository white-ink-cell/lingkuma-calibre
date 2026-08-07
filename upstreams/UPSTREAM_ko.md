# 업스트림 프로젝트 및 포팅 설명

[English](UPSTREAM.md) | [简体中文](UPSTREAM_zh.md) | [日本語](UPSTREAM_ja.md) | **한국어**

이 프로젝트는 **LingKuma 1.1.0**의 비공식 Calibre 포팅 버전입니다.

- 원 프로젝트: `lingkuma/LingKuma`
- 업스트림 버전: LingKuma 1.1.0
- Calibre 포팅 버전 유지보수 / 배포: `white-ink-cell`

LingKuma 원 프로젝트의 저자 표기, 저작권, 라이선스 및 포함된 업스트림 리소스는 변경하지 않습니다.

## 포팅 버전의 주요 변경 사항

Calibre 포팅 버전은 주로 다음 기능을 추가합니다.

1. LingKuma 외부의 Calibre / Qt WebEngine 호환 레이어.
2. Calibre 독서 콘텐츠에 맞는 문장 경계 판정 및 텍스트 재구성 규칙. 1.0에서는 일본어와 한국어의 5자 미만 의미 있는 짧은 문장이나 구절도 둘 이상의 어휘 단위를 포함하면 Word Explosion을 열 수 있습니다.
3. LingKuma의 기존 테마 및 팝업 로직을 유지하면서 제공하는 Calibre 호환 반투명 유리 효과.
4. 다국어 번역, AI 출력 및 관련 언어 메타데이터를 위한 원문 언어와 대상 언어 처리.

Calibre 전용 동작은 가능한 한 adapter / host / compatibility 레이어에 분리하며, 포함된 LingKuma 업스트림 리소스의 원 저작자 표기와 라이선스를 유지합니다.
