# LSPosed 独立定时启动与执行

日期：2026-10-23；模块版本：0.4.0。

## 已部署行为

调度、启动弹窗处理、开始冒险、主城就绪判断和完整助手执行均已迁入模块 APK，不再依赖 AutoJs 或截图模板。当前设备已开启每天北京时间07:00运行；普通手动打开游戏不会自动开始冒险或执行助手。配置应用提供立即运行、仅验证启动、30秒定时验证和停止按钮。

用户明确授权后，仅为 `com.zfj.dldlextension` 新增永久 Root 权限。LSPosed 作用域仍只有游戏 `com.hnzh.dldlwhjx.huawei`，主入口为 `com.game.sdk.GameSdkActivity`。原角色绑定、助手开关、执行次数和持久消费记录保留。

## 实现与边界

- 应用侧使用 `AlarmManager.setExactAndAllowWhileIdle`，以 `Asia/Shanghai` 计算07:00；每次触发先预约下一日。开机及校时重新预约。前台服务持有最长40分钟 CPU 唤醒锁，Root 命令限制20秒和64KiB输出。
- Root 仅负责唤醒、启动游戏及私有指令/回执传递。服务和接收器不导出；启动指令300秒有效，原子写入并恢复游戏 UID 和 SELinux 标签。
- Java Hook 在有效自动启动期间，让 `JosGetNoticeResp.getNoticeIntent()` 和 `GameNoticeResp.getNoticeIntent()` 不提供推广窗口；`AppUpdateActivity.c(ApkUpgradeInfo)` 仅取消可选更新，调用 SDK 原有 `finish()` 保留回调。强制更新保留显示并报告阻塞。
- Lua 在游戏 GL 线程调用已恢复的官方登录入口 `selected_view:onEnterGame()`，每个请求只调用一次。普通公告走 `NoticeController:closeNoticeView()`，强制公告保留。登录协议未勾选、服务器不符等情况停止，不自行修改。
- 检查连接、角色、登录窗消失、主UI及助手模型，连续稳定3秒才提交完整队列。提交后助手会隐藏主UI，因此只检查连接、角色及业务回执，避免完成结果被主城等待遮住。
- 既有完整助手仍按角色、服务器、北京时间05:00刷新的游戏日持久去重。上次未确认则返回 `uncertain`；不清 journal，不自动重跑可能消费资源的请求。

## 实机验证

设备为 Redmi Note 12T Pro，Android15，ReSukiSU / LSPosed API102。证据置于已忽略的 `evidence/phase15/`，不将角色与私有配置提交仓库。

|验证|结果|
|---|---|
|自动冷启动|日志确认拦截 SDK 推广、取消可选更新、调用开始冒险，抵达主城并返回 `verified / city_and_role_ready`|
|熄屏定时|30秒测试闹钟于01:09:27实际触发，唤醒并冷启游戏，01:10:04返回verified；未执行助手业务|
|完整助手|本次45条均取得终态：32条executed、13条skipped；业务回执 `completed / queue_finished / 45 / 45`|
|完成收尾修复|发现助手结果页隐藏主UI后收尾等待不退出，修正状态机，并增加主UI关闭时仍能读取completed的回归|
|修复后冷启动|01:18:55返回 `already_completed / daily_run_completed`，未重跑队列；01:18:57自动关闭游戏，清理launch，退出服务并释放唤醒锁|
|普通启动|无launch，无自动服务，startup终态保持上次结果；可选更新按官方方式显示，按返回关闭后保持“开始冒险”页，没有自动进入或执行|
|每日预约|系统确认下一次 `RTC_WAKEUP` 为2026-10-23 07:00:00，window=0|

完整队列使用原有用户设置，包含官方商店等消费任务；本次结果截图显示杂货店按既有配置刷新购买，消耗40钻石及7500K金币。`completed` 表示队列处理结束，跳过项仍可能是无剩余次数、资源不足或当天已做，不表示每项都领取成功。

原完整业务结果与助手截图先于收尾修复取得；修复后通过状态机回归和当天已完成的冷启动复验验证终态收集，没有清除当天去重记录来重复消费。最终 `tasks.tsv` 仍保留45条结果。

## 后台冻结排查与迁移

初次验证发现小米 Greezer 冻结了模块，进程的 `cgroup.freeze=1`，CPU锁被标记DISABLED；前台服务和电池白名单单独不足以避免此情况。仅将该模块 PowerKeeper 的 `bgControl` 调整为 `noRestrict` 并允许自启动。修正后冷启动及时收尾，熄屏定时测试也通过。未修改其他应用或第三方模块的配置。

已停止 AutoJs6 并仅移除其指向 `/data/user/0/org.autojs.autojs6/files/dldl/run-helper.js` 的旧定时记录；窄查询确认删除1条、其他任务0条。只备份该任务记录，没有导出整个数据库。旧脚本和配置保留，旧活动闹钟消失，新模块DAILY闹钟保留。

## 本地校验与交付

以下检查全部通过：

```sh
PYTHONPATH=.tools python3 tests/test_startup_automation.py
PYTHONPATH=.tools python3 tests/test_helper_automation.py
PYTHONPATH=.tools python3 tests/test_extension_loader.py
bash tests/test_launch_request.sh
cd lsposed-module
./gradlew :app:assembleDebug :app:lintDebug --offline
```

加载器测试包含已有111项回归和生命周期验证。Lint 无错误，保留8项警告，涉及目标 API、Root 私有目录路径、备份规则、应用图标和文本国际化。最终APK已覆盖安装，保留配置；路径为 `lsposed-module/app/build/outputs/apk/debug/app-debug.apk`。

SHA-256：`07fda28dd51bf8764f96ef3b6a89560d8c2d69c3fa048b0c4536890c513b7207`。

操作说明见 [独立自动运行](../lsposed-module/docs/automation.md)。此前的 [AutoJs阶段报告](20_每天定时完整助手自动化.md) 仅保留历史记录，当前调度已迁移。

## 尚未验收

尚未等到整夜待机后的07:00观察实际每日触发，短时熄屏测试不能替代此项。密码锁屏、验证码、强制更新、未知弹窗及接口变化可能需要人工处理；仅对当前已识别的窗口和官方业务接口完成适配。未来客户端覆盖升级、热更新、重启后的长期调度仍需另行验收。
