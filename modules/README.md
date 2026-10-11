# 香香小助手自定义日常模块

「日常」页共八行：斗罗集市每日／每周／每月免费礼包、学院活动每日特惠、乾坤问情谷免费扫荡、众神殿膜拜、魂域之境膜拜、镜之屋每日契约召唤。

新增六行默认关闭，原开关保留。镜之屋支持 10／20 次，只使用灵魂契约：开始前检查全部剩余目标，20 次分两次十连，不足、超时或背包满就停止，不走钻石分支。每天 05:00 刷新本模块额度；手动抽取不计入该额度。乾坤问情谷只扫最高通关层的每日免费次数，不使用扫荡券。

- `daily_gifts.lua`：21017/21018 免费礼包状态机。
- `daily_actions.lua`：扫荡、膜拜、召唤的串行状态机。
- `daily_actions_game.lua`：真实游戏接口与持久化记录。
- `xiangxiang_gifts_extension.lua`：原生 UI、设置、队列接入；本地编号不发给服务器。

测试：`PYTHONPATH=.tools python3 tests/test_daily_actions.py`（26 项，使用真实恢复代码，网络为离线模拟）。构建：`PYTHONPATH=.tools python3 scripts/build_gifts_bundle.py`。部署与实际验证见 [报告 12](../reports/12_六项日常功能扩展.md)。

原两项领取已由用户验证正确；本轮实机已完成免费周／月礼包及两处膜拜，20 次召唤因契约不足正确阻断，扫荡无可执行项而跳过。新任务保留原奖励窗口；未确认结果不会自动重发。热更新覆盖后须核对版本与哈希再部署。

`daily_sign.lua`／`xiangxiang_sign_extension.lua` 是历史修炼补给原型，未部署；`loader_probe.lua` 是历史加载探针。
