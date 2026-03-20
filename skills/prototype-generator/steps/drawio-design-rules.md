# draw.io 设计规则（主 Agent 审视使用）

> 此文件由主 Agent 在 Step 5-5 校验和 Step 6 审视时加载，subagent 不需要加载。

---

## 输出文件规则

| 规则 | 要求 |
|------|------|
| **一个模块一个文件** | 每个功能模块生成独立的 `.drawio` 文件，文件内用多个 `<diagram>` 存放多个状态页 |
| **一个页面一个分组** | 同一画布内，每个页面用 `swimlane` 容器包裹，`value` 为页面名 |
| **连线必须有标签** | 所有 `edge` 的 `value` 不可为空，至少写 `动作-目标` |
| **弹窗挂载来源页** | 确认弹窗、错误弹窗等绘制在触发它的页面分组容器内部 |

### 页面分组容器写法（swimlane）

```xml
<mxCell id="100" value="订单-列表页" style="swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;" vertex="1" parent="1">
  <mxGeometry x="20" y="20" width="420" height="860" as="geometry" />
</mxCell>
<!-- 容器内的元素 parent 指向容器 id，而非 "1" -->
<mxCell id="101" value="订单列表" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;" vertex="1" parent="100">
  <mxGeometry x="0" y="0" width="420" height="48" as="geometry" />
</mxCell>
```

---

## 校验规则

| 规则 | 检查方式 |
|------|----------|
| **不允许孤立页面** | 每个页面分组必须至少有一条连线（进入或离开） |
| **不允许无去向主按钮** | 每个主按钮（蓝色填充）必须有 `tooltip` 或对应的 `edge` 连线 |
| **不允许缺失关键业务闭环** | 列表→详情→操作→结果→返回列表的路径必须完整连通 |
| **不允许只画 happy path** | 每个核心页面必须包含空态或异常态的标注 |

**自查输出格式：**

```
=== draw.io 校验报告 ===
✅ 无孤立页面（共 N 个页面，全部有连线）
⚠️ 发现 X 个主按钮无跳转标注，已补充 tooltip
✅ 业务闭环完整（列表→详情→操作→返回路径连通）
⚠️ 发现 Y 个页面缺少空态/异常态，已补充状态标注
```
