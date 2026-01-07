# maim-Selfie

> *kamisama tell me how to visualize our maim*

---

## // WHAT IS THIS

让麦麦学会「自拍」的插件。

基于 Gemini 生图能力，将麦麦的人设与当前活动转化为可视化图像。
她可以主动决定拍照，也会在日程切换时随机触发。

**不是 AI 生图工具。是让 AI 拥有「被看见」的能力。**

---

## // FEATURES

```
[■] LLM 工具调用    — 麦麦自己决定什么时候拍
[■] 活动变化触发    — 日程切换时小概率自动触发
[■] 双视角模式      — 自拍 / POV 第一人称
[■] 双风格模式      — 精美照片 / 随手拍
[■] 时间感知        — 光线随真实时间变化
[■] 人设参考图      — 可配置角色形象文件夹
[■] Gemini 2.5 兼容 — 自动识别模型版本
```

---

## // INSTALLATION

```bash
# 将插件放入 MaiBot/plugins/ 目录
cp -r uaih3k9x_selfie_plugin /path/to/MaiBot/plugins/
```

编辑 `config.toml`，填入你的 API 配置。

---

## // CONFIGURATION

```toml
[selfie.api]
api_base = "your-api-endpoint"
api_key = "your-api-key"
model = "gemini-2.5-flash-preview-native-audio-image"

[selfie.style]
professional_ratio = 0.3    # 30% 精美照片
selfie_ratio = 0.5          # 50% 自拍视角
```

---

## // COMMANDS

```
/selfie              — 自动获取当前活动，随机风格
/selfie 吃饭         — 指定活动
/selfie 学习 pov     — 指定活动和视角
/selfie 散步 selfie professional — 完整参数
```

---

## // LICENSE

MIT License

---

<p align="center">
  <sub>// KIRISAME SYSTEMS™ | uaih3k9x</sub><br>
  <sub>// "We shape the void."</sub>
</p>
