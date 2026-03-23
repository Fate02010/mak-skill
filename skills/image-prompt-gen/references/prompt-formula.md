# 提示词构建原则

## 核心公式

一个优质的 AI 图片提示词由以下模块组成（顺序建议）：

```
[主体描述] + [动作/状态] + [环境/背景] + [光照] + [色调] + [艺术风格] + [构图/镜头] + [质量修饰词]
```

## 各模块说明

### 1. 主体描述（Subject）— 必填

描述画面的核心对象，越具体越好。

| 描述层次 | 示例 |
|----------|------|
| 模糊 | a girl |
| 一般 | a young Asian woman |
| 优质 | a young Asian woman in her 20s, short black hair, wearing a white linen dress |

**原则**：种族/年龄/特征/服饰，能说具体就说具体。

### 2. 动作/状态（Action/Pose）— 推荐

主体在做什么？什么状态？

- `standing, looking at the camera`
- `walking through rain, umbrella in hand`
- `sitting by the window, reading a book, soft smile`

### 3. 环境/背景（Setting/Environment）— 推荐

场景在哪里？什么时间？什么天气？

- `in a cozy coffee shop, warm interior lighting`
- `on a misty mountain trail at dawn`
- `Tokyo street at night, neon signs reflected on wet pavement`

### 4. 光照（Lighting）— 核心影响氛围

光照是提示词中影响最大的单一变量。

| 光照类型 | 描述 | 情绪 |
|----------|------|------|
| `golden hour light` | 日出日落时的温暖侧光 | 温暖、浪漫 |
| `soft diffused light` | 散射柔光，无强烈阴影 | 柔和、温柔 |
| `dramatic studio lighting` | 强对比硬光 | 戏剧、力量 |
| `overcast natural light` | 阴天均匀光 | 平静、忧郁 |
| `moonlight, blue tones` | 月光，蓝色调 | 神秘、宁静 |
| `neon glow, night city` | 霓虹灯光 | 赛博、夜生活 |
| `candlelight` | 烛光，温暖小范围光 | 亲密、复古 |
| `volumetric light, god rays` | 体积光，光束穿透 | 史诗、神圣 |

### 5. 色调/调色（Color & Palette）— 推荐

明确主色调可以大幅提升一致性。

- `warm earth tones, amber and sage`
- `monochromatic blue palette`
- `muted pastel colors, soft and dreamy`
- `high contrast black and white`
- `rich jewel tones, deep emerald and burgundy`
- `Morandi color palette`（莫兰迪色调）

### 6. 艺术风格（Art Style）— 必填（来自风格文件）

从 `references/styles/<style>.md` 读取对应风格的核心 prompt 关键词。

### 7. 构图/镜头（Composition/Camera）— 推荐

| 构图类型 | 英文关键词 |
|----------|------------|
| 特写 | `close-up`, `tight portrait` |
| 半身 | `medium shot`, `waist-up` |
| 全身 | `full body shot` |
| 广角 | `wide angle`, `establishing shot` |
| 俯视 | `bird's eye view`, `top-down perspective` |
| 仰视 | `low angle shot`, `dramatic upward angle` |
| 黄金构图 | `rule of thirds composition` |
| 对称构图 | `symmetrical composition` |

**相机/镜头词（摄影风格专用）**：
- `shot on Sony A7IV, 85mm f/1.4`
- `Leica M10, 35mm lens, film grain`
- `shot on iPhone, candid, documentary style`

### 8. 质量修饰词（Quality Modifiers）— 推荐

根据目标模型调整：

**通用**（大多数模型有效）：
- `highly detailed`, `intricate details`
- `8K resolution`, `ultra-high resolution`
- `professional photography`, `award-winning`

**Midjourney 特有效果好**：
- `--style raw`（更写实）
- `--v 7`（最新版本）

**DALL-E / GPT-Image**：不建议堆砌质量词，自然语言描述更有效。

**Stable Diffusion / Flux**：
- `masterpiece, best quality, ultra-detailed`
- 负面提示词：`ugly, blurry, low quality, watermark, text`

## 构建示例

**用户输入**：一只在雨中行走的猫，电影感

**构建过程**：
1. 主体：`a fluffy tabby cat`
2. 动作：`walking through rain, wet fur, paw splashing in a puddle`
3. 环境：`city alley at night, rain-soaked cobblestones`
4. 光照：`dramatic side lighting, streetlamp glow, rain reflections`
5. 色调：`cool blue and orange tones, cinematic color grading`
6. 风格：（读取 cinematic-photo.md）`cinematic photography, 35mm film, anamorphic lens`
7. 构图：`low angle shot, shallow depth of field`
8. 质量：`ultra-detailed, 8K, professional photography`

**最终提示词**：
```
a fluffy tabby cat walking through rain at night, wet fur, paw splashing in a puddle, city alley, rain-soaked cobblestones, dramatic side lighting from a streetlamp, rain reflections, cool blue and orange cinematic color grading, cinematic photography, 35mm film, anamorphic lens, low angle shot, shallow depth of field, ultra-detailed, 8K
```

## 常见错误

| 错误 | 示例 | 改进 |
|------|------|------|
| 描述太宽泛 | `a beautiful woman` | `a 25-year-old Japanese woman with wavy black hair, wearing a vintage red qipao` |
| 堆砌形容词 | `amazing beautiful stunning gorgeous` | 具体描述代替修饰词 |
| 忽略光照 | 无光照信息 | 加上 `golden hour light` / `soft studio lighting` 等 |
| 忽略比例 | 无 `--ar` | 明确指定目标比例 |
| 与风格冲突 | 水墨风 + `photorealistic` | 风格内部保持一致 |
