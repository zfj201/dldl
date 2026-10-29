# 香香小助手扩展 · Android 模块

《斗罗大陆：武魂觉醒》华为渠道版的 LSPosed 扩展，当前版本 **0.6.2**。为游戏内香香小助手增加 17 项日常任务，以及敏堂自动派遣与刷新、极地矿场每日挑战、联盟红包自动领取，并提供每天北京时间 07:00 的独立自动运行。

完整功能列表、资源消耗说明与常见问题见[项目首页](../README.md)。

## 安装使用

需要 Android 10+、arm64 和支持现代 libxposed API 102 的 LSPosed 环境。当前适配游戏包名为 `com.hnzh.dldlwhjx.huawei`。

1. 安装模块 APK，在 LSPosed 中启用模块，作用域仅勾选游戏，然后重启游戏。
2. 手动进入主城，打开香香小助手，在“日常”或“其他自动化”中开启所需任务并保存。新增任务初次默认关闭。
3. 需要定时运行时，打开“香香小助手扩展”配置应用，授予模块自身 Root 权限并绑定当前角色。
4. 允许精确闹钟、通知、自启动和后台运行，先通过“仅验证启动”和“30秒后验证定时启动”检查配置，再开启每日 07:00 自动运行。

普通手动启动游戏不会自动执行任务。“立即运行完整助手”使用与每日调度相同的流程；仅验证启动不会执行任务。敏堂允许钻石刷新且没有消费上限，开启前请阅读[功能说明](../README.md#其他自动化)。

停用定时运行可关闭配置页的每日开关；完全停用扩展时，关闭 LSPosed 模块并重启游戏。更新安装需保持 APK 签名一致。

## 从源码构建

推荐环境：Android Studio、JDK 21、Android SDK 37、NDK r27d、Python 3。当前 native 构建脚本适配 macOS。

在本目录的 `local.properties` 配置 `sdk.dir` 和 `ndk.dir`，也可通过 `ANDROID_NDK_HOME` 指定 NDK。路径配置和签名密钥不应提交到仓库。

在本目录运行：

```sh
./gradlew :app:assembleDebug :app:lintDebug
```

Gradle 会自动构建 JNI 桥并将 Lua 业务源码打包进 APK。开发包输出路径：

```text
app/build/outputs/apk/debug/app-debug.apk
```

正式分发应使用独立的发布签名，并保管好密钥，以便后续覆盖升级。

## 源码结构

| 路径（相对仓库根目录） | 内容 |
| --- | --- |
| `lsposed-module/app/src/main/java/` | LSPosed 入口、模块配置、定时调度和启动恢复 |
| `lsposed-module/app/src/main/cpp/` | 游戏 Lua 接口的 JNI 桥 |
| `lsposed-module/lua/bootstrap.lua` | 等待游戏初始化并挂载扩展 |
| `modules/xiangxiang_gifts_extension.lua` | 日常菜单、任务设置和执行结果 |
| `modules/daily_*.lua` | 礼包、挑战、膜拜、召唤、养成等日常任务 |
| `modules/voyage_automation*.lua` | 其他自动化分类、敏堂派遣刷新和完整明细 |
| `modules/mine_automation*.lua` | 极地矿场50层1区每日挑战 |
| `modules/redbag_automation*.lua` | 联盟红包筛选、串行领取与奖励汇总 |
| `modules/helper_automation*.lua` | 完整助手队列、角色绑定和执行去重 |
| `modules/startup_automation*.lua` | 开始冒险、主城检查和启动流程 |
| `lsposed-module/scripts/` | native 构建与 Lua 打包 |
| `tests/` | 离线联调和启动恢复测试 |

扩展使用游戏现有接口，在渲染线程执行 Lua，不覆盖官方启动文件。APK 内的 Lua 包由源码生成，修改业务逻辑应编辑 `modules/` 中的文件。

## 验证与兼容性

从仓库根目录可运行主要 Lua 测试：

```sh
PYTHONPATH=.tools python3 tests/test_extension_loader.py
PYTHONPATH=.tools python3 tests/test_voyage_automation.py
PYTHONPATH=.tools python3 tests/test_mine_automation.py
PYTHONPATH=.tools python3 tests/test_redbag_automation.py
PYTHONPATH=.tools python3 tests/test_helper_automation.py
PYTHONPATH=.tools python3 tests/test_startup_automation.py
```

测试依赖 Lua 5.1/Lupa 和本地已恢复的游戏类；原始游戏资源不随源码提供，纯源码检出不足以运行全部联调。

游戏及 SDK 更新可能改变接口和弹窗流程。当前模块仅处理已识别的可选更新和推广，保留强制更新与人工登录验证。调度配置和诊断方法见[自动运行说明](docs/automation.md)，实机验证范围见[敏堂报告](../reports/26_敏堂自动派遣与刷新实现.md)及[矿场报告](../reports/27_极地矿场每日挑战与双任务启用.md)。
