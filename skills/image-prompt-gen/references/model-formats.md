# 不同模型的提示词语法

## 通用原则（Generic）

默认输出格式，适配大多数模型。结构化描述，英文输出。

```
[subject], [action], [setting], [lighting], [color palette], [art style], [composition], [quality]
```

---

## Midjourney

### 语法特点

- 提示词后附参数（`--param`）
- 支持权重语法：`cat::2 dog::1`（猫的权重是狗的两倍）
- 支持多提示词混合：`/imagine prompt: a cat | a dog`

### 常用参数

| 参数 | 示例 | 说明 |
|------|------|------|
| `--ar` | `--ar 16:9` | 宽高比 |
| `--v` | `--v 7` | 版本（7 为最新） |
| `--style` | `--style raw` | raw = 更写实；不加 = 更艺术化 |
| `--chaos` | `--chaos 20` | 创意随机度（0-100） |
| `--no` | `--no text` | 排除元素（相当于负面提示词） |
| `--seed` | `--seed 12345` | 固定随机种子 |
| `--q` | `--q 2` | 质量（0.25/0.5/1/2） |

### 输出格式示例

```
a fluffy tabby cat walking through rain at night, city alley, dramatic side lighting, cinematic photography, 35mm film, low angle shot, ultra-detailed --ar 16:9 --v 7 --style raw
```

---

## DALL-E / GPT-Image（OpenAI）

### 语法特点

- 自然语言效果最好，无需质量词堆砌
- 详细的场景描述 > 短句堆叠
- 比例通过参数指定（不写在提示词里）
- 避免写"不要 xxx"——改成"只有 xxx"

### 提示词策略

- 描述性长句比碎片短词效果好
- 如"a cozy coffee shop interior with warm lighting, wooden furniture, and steam rising from a coffee cup on the table" 比 "coffee shop, warm, cozy" 效果好
- 不需要 `masterpiece`、`8K` 等质量词

### 输出格式示例

```
A fluffy tabby cat walks through a rainy city alley at night. The cat's fur is wet, and its paw is mid-splash in a puddle. A warm streetlamp casts dramatic side lighting, creating orange reflections on the rain-soaked cobblestones. The scene has a cinematic, film noir atmosphere with cool blue tones.
```

**参数**：比例和质量通过 API 参数控制，不写入提示词。

---

## Stable Diffusion（SD）/ Flux

### 语法特点

- 使用**正向提示词** + **负向提示词**（Negative Prompt）两部分
- 支持权重增强：`(keyword:1.5)` 或 `((keyword))`
- 质量词有效：`masterpiece, best quality, ultra-detailed`

### 正向提示词格式

```
masterpiece, best quality, ultra-detailed, [subject], [action], [setting], [lighting], [color palette], [art style], [composition], 8K, high resolution
```

### 负向提示词（通用底模）

```
ugly, blurry, low quality, low resolution, watermark, text, signature, extra limbs, deformed, disfigured, bad anatomy, worst quality, jpeg artifacts
```

### 权重用法

- `(golden hour light:1.3)` — 增强光照描述
- `(cat:1.2)` — 强调猫咪主体
- `[background]` — 降低背景权重（SD1.5 语法）

### 输出格式示例

```
[正向]
masterpiece, best quality, (fluffy tabby cat:1.2), walking through rain, city alley at night, (dramatic side lighting:1.3), neon reflections on wet cobblestones, cinematic photography, 35mm film aesthetic, cool blue and orange tones, ultra-detailed, 8K

[负向]
ugly, blurry, low quality, watermark, text, extra limbs, deformed
```

---

## Flux

### 语法特点

- 比 SD 更接近自然语言
- 负面提示词效果较弱，不必强调
- 自然描述 + 少量质量词即可

### 输出格式示例

```
A tabby cat walking through a rainy city alley at night, wet fur glistening under dramatic streetlamp light, rain-soaked cobblestones, cinematic color grading with cool blue and warm orange tones, 35mm film style, highly detailed
```

---

## 通义万象（DashScope / Qwen-Image）

### 语法特点

- 支持中文提示词（中文效果良好）
- 英文也支持，效果接近
- 不需要质量词堆砌
- 支持 `负向提示词`（API 参数）

### 中文提示词格式示例

```
一只毛茸茸的虎斑猫在雨夜穿过城市小巷，皮毛湿透，爪子踩在水坑里溅起水花，路灯的戏剧性侧光照亮了雨后的鹅卵石路面，电影感色彩，冷暖色对比，写实摄影风格
```

### 适合场景

- 需要中文内容（如文字融合）的场景
- 中国文化相关内容
- 人物肖像

---

## 不同模型的对比选择

| 需求 | 推荐模型 |
|------|----------|
| 写实摄影 | DALL-E / GPT-Image，通义万象 |
| 艺术插画 | Midjourney v7 |
| 精细控制 | SD / Flux（支持 ControlNet、LoRA） |
| 中文字体/内容 | 通义万象 Qwen-Image-2.0-Pro |
| 快速迭代 | Flux（速度快） |
| 概念艺术 | Midjourney |
