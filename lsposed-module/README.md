# 香香小助手扩展

独立 Android Studio 项目，位于 `zfj201/dldl` 仓库的 `lsposed-module/`。现代 libxposed API 102，Android 10+、arm64。仅作用于 `com.hnzh.dldlwhjx.huawei` 主进程。

## 工作方式

以前是把扩展接在游戏的 `game_start` 文件后面，游戏读这个文件时顺便启动扩展。现在扩展单独装在模块 APK 里，由 LSPosed 在游戏进程启动后把它带进去，再请游戏自己的 Lua 接口运行它。业务逻辑沿用原来的 Lua，换的是启动入口，不再改官方启动文件。

模块给官方香香小助手加菜单；普通手动打开游戏不会自动做任务。0.4.0 起，模块自身提供北京时间每天07:00调度、“立即运行”和不执行任务的启动诊断。由 LSPosed 处理已识别的 SDK 推广/可选更新，调用游戏内开始冒险逻辑，确认主城与绑定角色后执行完整助手。无需 AutoJs 或图片模板。配置、权限、协议及限制见 [独立自动运行](docs/automation.md)。

0.4.1 起，自动启动时华为“正在加载中...”框连续显示超过15秒会杀进程重启，每次最多3次。离开该框重新计时；已进入登录或助手执行阶段不会触发这项恢复，普通手动启动不触发。

0.5.1 补齐华为 JOS / 账号 SDK 推广入口，并处理华为登录进程内部弹出的图片推广：模块仅在有效自动指令期间，核对游戏任务、推广控件和窗口后正常点击原生关闭控件，位置来自当前控件边界。已实机自动关闭两张推广并进入主城；普通手动启动保持原流程。见[推广拦截修复记录](../reports/24_华为启动推广拦截补齐.md)。

0.5.0 新增联盟幻境每日挑战一次、决战武魂殿每日挑战一次、魂导器工坊每日免费礼包三个独立开关，默认关闭。挑战以成功发起回执为完成，不跳过、不等结算；第二场被明确拒绝且助手自己的前一场仍在战斗时，先继续其他任务，后台重新核对次数后仅补发一次。自动关闭游戏会等补发处理结束。工坊只领取高级晶片×1、初级晶片×100的免费礼包。详见[三项扩展报告](../reports/23_联盟幻境武魂殿与工坊礼包.md)。

LSPosed 在进程启动时加载小型 JNI 桥，在 `Cocos2dxRenderer.onDrawFrame` 原方法结束后，每秒一次调用游戏已有的 `Cocos2dxLuaJavaBridge.callLuaGlobalFunctionWithString`。通过 `dofile` 执行独立引导器，不使用固定 RVA、Lua_State 指针或 native inline hook。渲染尚未初始化则不调用。

官方 `game_start` 完成后安装 17 项入口；收到执行操作或自动化指令后才执行任务。控制器、窗口类、配置列表或 beginGame 对象变化时重新挂载；同一代次不重复安装。安装失败回滚自己已改动的方法；不清配置或消费 journal。历史单笔修复入口不进入发布包。

native 和 Lua SHA-256 来自签名 APK 内资源。复制到游戏 `files/dldl_extension/bundle-<hash>/`，逐文件校验并原子替换。冷启动会恢复缺失或损坏的副本。官方资源哈希不作为长期启动门槛，也不会被模块覆盖。

## 从哪里读核心代码

0.6.1 在左侧“商店”之后的“其他自动化”提供敏堂派遣/刷新与极地矿场每日挑战。敏堂按品质和目标奖励筛选、派完再刷新，情报不足停止，全部派遣逐笔显示并保留历史。矿场固定50层1区，使用已有三队伍进攻阵容，优先选择符合条件的闲置矿点，成功发起即完成，不等待结算；按北京时间05:00游戏日去重。两项初次默认关闭，开启保存后加入原07:00全分类队列。详见[敏堂实现](../reports/26_敏堂自动派遣与刷新实现.md)及[矿场验证](../reports/27_极地矿场每日挑战与双任务启用.md)。

| 位置（相对仓库根目录） | 负责什么 |
| --- | --- |
| `lsposed-module/app/src/main/java/com/zfj/dldlextension/DldlModule.java` | LSPosed 入口、等待引擎初始化、借用游戏渲染线程调用 Lua |
| `lsposed-module/app/src/main/java/com/zfj/dldlextension/PayloadStore.java` | 从模块 APK 取 Lua，校验并恢复独立副本 |
| `lsposed-module/app/src/main/cpp/bridge.c` | 小型转接器，调用游戏已有 Lua 接口 |
| `lsposed-module/lua/bootstrap.lua` | 等官方业务准备好，判断是否已挂载，必要时拆旧挂新 |
| `modules/xiangxiang_gifts_extension.lua` | 17项菜单、设置、队列分派、结果显示和卸载回滚 |
| `modules/daily_gifts.lua` | 免费礼包领取流程 |
| `modules/daily_actions.lua` / `daily_actions_game.lua` | 扫荡、膜拜、契约召唤的流程及游戏接口适配 |
| `modules/daily_training.lua` / `daily_training_game.lua` | 积分赛、魂师升级、背包魂骨强化的流程及游戏接口适配 |
| `modules/daily_quests.lua` / `daily_quests_game.lua` | 宗门祈愿奖励、至高遗迹的流程及游戏接口适配 |
| `modules/daily_extras.lua` / `daily_extras_game.lua` | 两项每日发起挑战、后台补发及工坊免费晶片礼包 |
| `modules/voyage_automation.lua` / `voyage_automation_game.lua` | 其他自动化分类、敏堂串行派遣与刷新、全部明细与历史 |
| `modules/mine_automation.lua` / `mine_automation_game.lua` | 极地矿场50层1区每日挑战、三队伍验证和发起确认 |
| `modules/helper_automation.lua` / `helper_automation_game.lua` | 自动执行完整助手列表、角色和游戏日绑定、持久去重及完成回执 |
| `modules/startup_automation.lua` / `startup_automation_game.lua` | 单次开始冒险、公告正常关闭、主城稳定检查和启动诊断 |
| `lsposed-module/app/src/main/java/com/zfj/dldlextension/AutomationService.java` / `DailySchedule.java` | 模块应用的精确闹钟、Root启动、前台保活和结果收集 |
| `lsposed-module/scripts/build-payload.py` | 把上述源码打包成 APK 内独立 Lua，不拼入官方 game_start |

优先读 `bootstrap.lua` 的挂载判断和 `xiangxiang_gifts_extension.lua` 的 `requestTask` 包装，分别对应“扩展怎么进来”和“点执行后怎么工作”。`app/src/main/assets/extension/payload.lua` 是构建生成文件，不是维护业务逻辑的位置。

## 构建

Android Studio JDK 21、SDK 37、NDK r27d。`local.properties` 指定 `sdk.dir`、`ndk.dir`，或用 `ANDROID_NDK_HOME` 指定 NDK；本地配置不提交。NDK 构建脚本当前适配 macOS。

```sh
./gradlew :app:assembleDebug :app:lintDebug
```

Gradle 自动构建 JNI 桥、生成独立 Lua 包及 manifest。开发 APK 位于 `app/build/outputs/apk/debug/app-debug.apk`，默认阶段5。`-PprobeStage=1/2/3/4` 可分别构建 Java、空 native、渲染观察、单次 Lua 探针。阶段2/3不会调用新增 native 执行函数。

```sh
PYTHONPATH=.tools python3 tests/test_extension_loader.py
```

上述测试从仓库根目录运行，依赖本机 Lua 5.1/Lupa 与已恢复游戏类，包含已有111项回归及加载器生命周期检查，不调用设备或网络。新增三项集成测试：`PYTHONPATH=.tools python3 tests/test_daily_extras.py`，共132项，含后台补发、提前关闭防护与礼包配置变更验证。

自动化测试：`PYTHONPATH=.tools python3 tests/test_helper_automation.py`、`PYTHONPATH=.tools python3 tests/test_startup_automation.py`、`sh tests/test_launch_request.sh`、`sh tests/test_loading_recovery.sh`。自动化通道位于游戏 `files/dldl_extension/automation/`，协议及定时安装见 [独立自动运行](docs/automation.md)。

## 使用与回退

在 LSPosed 中启用模块、仅勾选游戏，重启游戏。打开游戏内香香小助手，在日常页或“其他自动化”设置并保存。敏堂与矿场均开启后会加入每天07:00全分类队列；普通手动打开游戏不自动执行。停用模块并重启游戏即可回到官方助手；消费 journal 与偏好保留。

旧 `game_start` 组合包必须先按当前资源版本精确迁移。发现 `DLDL_DAILY_GIFTS` 或相同自定义 ID 时，模块拒绝重复安装。不要把旧官方备份复制到已更新的游戏。

诊断：`files/dldl_extension/loader.log`，对应 bundle 下的 `status.txt` / `status.log`。创建 `files/dldl_extension/disabled` 可暂停挂载；已打开助手则等其关闭再卸载。移除此文件恢复挂载。通常直接使用 LSPosed 总开关即可。

APK 为本机开发签名；更新须保持签名密钥。正式发布应配置专用签名，密钥与密码不得提交 Git。没有在线代码下载。

## 实测边界

阶段进展与实际证据见 [自动挂载报告](../reports/19_LSPosed自动挂载验证与开发.md) 和 [独立定时与执行报告](../reports/21_LSPosed独立定时启动与执行.md)。业务函数、Java JNI 接口、ABI、框架或初始化流程变化时仍可能失效。真实游戏 APK 覆盖升级及热更新尚未完成验收，不保证所有未来版本。
