# 每天 07:00 执行完整香香小助手

AutoJs6 负责唤醒无密码手机、启动游戏、关闭已识别广告/公告、进入角色；LSPosed 扩展负责运行游戏原生的完整助手队列。运行不依赖电脑或 ADB。任务开关和次数沿用游戏内保存的设置，包括官方类别与自定义日常条目。

## 文件与依赖

- `run-helper.js`：开屏、页面识别、角色确认、发送一次执行指令、等待回执、成功后关闭游戏。
- `setup-schedule.js`：用 AutoJs6 `tasks` 接口注册每天 07:00 的持久精确闹钟。只替换本脚本路径的任务。
- `config.example.json`：角色绑定与模板配置示例；实际配置不要提交。
- `templates/`：当前客户端的按钮字样、关闭按钮和主城标签裁图，无账号信息。

手机需要 AutoJs6 6.7.0、Root、启用的香香小助手扩展 0.3.0+。已授权精确闹钟、后台运行和电池优化豁免。使用 Root 截图与输入，无需脚本申请共享存储或 MediaProjection 截图授权。无障碍服务不属于脚本依赖。

当前 Root 命令用 `su -M -c`，已在 ReSukiSU/KernelSU 实测。`-M` 进入全局挂载命名空间，否则 Android 的应用数据隔离会让 AutoJs 即使取得 uid=0 也看不到游戏的私有目录。换用其他 Root 实现时需确认它支持该选项。

全部文件放在 AutoJs6 私有目录 `/data/user/0/org.autojs.autojs6/files/dldl/`，实际 `config.json` 填入目标角色的 `rid` 和 `srv_id`。文件归属必须是手机上 AutoJs6 的实际 UID；不能把开发设备的 UID 当成通用值。模板放在该目录下 `templates/`。

脚本与配置保存在 AutoJs 私有目录，卸载或清除 AutoJs 数据会删除它们及定时任务。LSPosed APK 自带业务代码，不依赖这些脚本来挂载扩展；AutoJs 只是额外的定时启动工具。

## 安装与定时

安装官方 AutoJs6，给该应用 Root，允许精确闹钟与后台运行，加入电池优化白名单；在厂商系统的应用设置中允许自启动。手机时区设为 `Asia/Shanghai`。先登录一次游戏、保存助手任务设置并部署上述私有文件。

运行定时配置：

```sh
adb shell am start -n org.autojs.autojs6/org.autojs.autojs.external.open.RunIntentActivity \
  --es path /data/user/0/org.autojs.autojs6/files/dldl/setup-schedule.js
```

立即运行一次：

```sh
adb shell am start -n org.autojs.autojs6/org.autojs.autojs.external.open.RunIntentActivity \
  --es path /data/user/0/org.autojs.autojs6/files/dldl/run-helper.js
```

这两条命令只用于安装/验证，日常由手机自己的 AlarmManager 唤醒。`schedule.json` 记录定时 ID。勿在系统设置中强制停止 AutoJs；Android 会暂停被强制停止应用的闹钟，重新打开应用后应再运行定时配置。重启后也需检查厂商自启动政策是否允许恢复闹钟。

暂停自动运行：在 AutoJs 定时任务页面删除本脚本的每天 07:00 任务。手动脚本仍可运行。停止当前脚本可能留下 `running.lock`；先确认没有运行中的脚本，再清理锁，不能同时启动两份。

## 执行与去重

脚本先检查游戏处于前台，用当前截图识别按钮位置，不靠固定等待时间点未知页面。图片统一缩放到 1080×2460，实际点击按原分辨率换算。主城使用灰度、原尺寸匹配，适应游戏空闲时压暗画面；还必须连续三轮拿到新鲜业务就绪回执。

游戏通道在 `/data/user/0/com.hnzh.dldlwhjx.huawei/files/dldl_extension/automation/`。`ready.tsv` 告知角色、服务器、游戏日及时间；`request.tsv` 原子写入执行请求；`result.tsv` 返回进度及终态；`tasks.tsv` 保存条目结果。业务适配与协议校验位于 `modules/helper_automation*.lua`。

请求有效期 240 秒，模块限制为最多 300 秒并校验角色、服务器及游戏日。游戏日按北京时间 05:00 刷新。模块在打开助手前先持久记录“本日已开始”，完成后记录“已完成”。重复请求返回 `already_completed`；中途进程退出或回执不明则返回 `uncertain`，不自动重跑可能消费道具的列表。自动执行记录只约束自动化入口，手动执行保持原有行为。

自动化调用 `saveOperateRequest(true)` 生成所有已启用类别的队列，再由游戏执行窗口推进。完成要求执行窗口结束且每条队列行均已处理。条目自身可能为领取成功、无次数跳过、资源不足跳过或未确认，不能把“整队结束”理解为每项都领取了奖励。

每条 Root 命令最多 20 秒，进入游戏最多 5 分钟，队列单步停滞最多 180 秒、总执行最多 30 分钟。失败留下截图和日志，停止本轮，不循环重发、不购买额外次数。成功或当天已完成时按配置关闭游戏。

## 排查与兼容性

AutoJs 私有目录中的 `last-run.log`、`last-tasks.tsv`、`screen.png` 是诊断材料，可能包含角色信息，不要公开提交。`debug:true` 可暂时开启逐步日志；默认关闭。

客户端的新广告、公告位置、登录页面、屏幕比例变化可能需要更新模板；陌生弹窗不会被盲点，未能确认就绪会超时。模板识别不能保证识别所有未来弹窗，也不能替代业务接口兼容验证。账号登录过期、验证码、密码锁屏、网络异常需人工处理。客户端可选 APK 更新目前选择“以后再说”，自动化不会执行 APK 更新或切换角色。

业务侧限制沿用已有模块，例如契约不足只跳过召唤、召唤不用钻石，消费未确认保留 journal。当前没有魂师大赛模块。

实机验证与定时证据见 [报告 20](../reports/20_每天定时完整助手自动化.md)。
