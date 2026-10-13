# LSPosed 自动挂载验证与开发

日期：2026-10-13。依据报告17分层验证；此文件随阶段推进更新。尚未完成真实 APK/热更新验收。

## 项目与对照

独立 Android Studio 项目位于 `lsposed-module/`，与分析材料共用 `zfj201/dldl` Git 仓库，分批提交。包名 `com.zfj.dldlextension`，libxposed API 102；作用域只有目标游戏主进程。

测试设备已安装 LSPosed 2.2.0 (7854)、Android 15、arm64。游戏启动页版本 v1.3.2942，保持既有 Phase12 game_start 组合文件及偏好不变。安装阶段不执行助手业务。

## 已验证

|阶段|实际证据|结论|
|---|---|---|
|0：不启用模块|PID 5809，登录主城、进入助手、后台恢复后同 PID|基线正常|
|1：空 Java 模块|两次冷启 PID 10298、12053，均写入 java_ready 并登录主城；首轮进入助手及后台恢复正常|当前环境未观察到由空 LSPosed 引起的退出|
|2：空 native 桥|PID 14526 同时记录 java_ready/native_ready，JNI tid 与 Java 一致；登录主城、助手、后台恢复同 PID|空 so 实际加载后未观察到退出|
|3：仅观察渲染回调|PID 16286，render_hook_ready，GLThread 80/tid 16354；回调先运行原方法再写标记|已找到实际 GL 线程入口，未使用固定地址|

阶段1系统退出记录只有测试主动强停，没有新发生的异常退出。原始截图、系统记录保存在本地 `evidence/phase13/`（含账号内容，不上传）。这些观测不能证明未来版本绝无检测。

## 下一层入口

Java 层存在 `Cocos2dxRenderer.onDrawFrame` 与 `Cocos2dxLuaJavaBridge.callLuaGlobalFunctionWithString(String,String)`。计划在原渲染回调完成后调用原游戏 JNI 接口执行本地 Lua，引擎自己处理 Lua 状态与栈；先观察线程再执行无业务探针。不采用固定 RVA，不安装 native inline hook，不拦截 exit/kill。

空 native 桥只实现 JNI_OnLoad 与返回当前 tid 的 ping，不访问引擎状态。NDK r27d 取自 Google 官方下载，ZIP 完整解压通过；本地构建 arm64-v8a、Android API29、16KiB 最大页对齐。

阶段2第一次打包使用压缩 native 库，现代 LSPosed 的 `base.apk!/lib/arm64-v8a` 路径无法加载，产生 UnsatisfiedLinkError。此轮不算通过。修正 `useLegacyPackaging=false` 后才记录 native_ready；不属于游戏自杀。

## Lua 桥与真实模块

阶段4 PID17769、GLThread82/tid17989，native调用原游戏JNI `dofile`，成功写出独立 `lua_probe.log`，返回0。登录主城与后台恢复后仍同 PID，未新增异常退出。

阶段5先保留旧组合包，实机状态为 `legacy_payload_present`、generation=0，确认不会重复安装。

当前文件 SHA-256 与 Phase12 已部署产物完全一致（e04492f…），官方原密文备份与该组合包的构建来源一致（033b45a…），启动页仍 v1.3.2942。保存 Phase12 回退副本与扩展偏好后，通过现有哈希保护的原子部署脚本恢复当前对应的官方密文。该精确哈希只用于本次迁移，不进入模块长期加载条件。

迁移后 PID24949，独立 bundle 成功记录 `installed:14:version=0.2.0`、generation=1，官方 game_start 不再包含自定义扩展。

## 工程实现与检查

- Gradle 自动构建小型JNI桥、纯Lua包、APK内SHA-256清单；NDK与SDK路径在不提交的local.properties中。
- 渲染完成且引擎已初始化后，每秒运行一次引导器。官方 game_start 加载成功、GAME_INITED 为真才检查业务代次。不会主动运行任务。
- 控制器实例、类、列表、beginGame身份作为代次依据；同代重复回调幂等。助手打开时等待关闭再卸载/重挂。
- 安装局部失败时回滚已安装的包装；使用rawget/rawset恢复实例原始属性，避免将旧继承方法固定到新实例。
- 拆除仅修改仍属于自己的包装与行，不覆盖后来他方的改动；不修改偏好/消费journal。
- 发布包移除历史单笔积分赛、遗迹和魂师恢复入口。未知pending仍保留，已确认目标的正常魂师恢复逻辑保留。
- 已有111项回归、5项战斗状态机回归通过；新增加载器验证覆盖局部安装失败回滚、无业务请求安装14项、20次重复调用、关闭/重新启用、代次变化重挂、journal保留和外来包装保留。
- `assembleDebug`、`lintDebug`通过。lint只有目标SDK/备份配置/图标与文案的提示，无错误。

真实官方APK覆盖升级、真实同进程热更新、新Lua状态重建仍未验收；不能把模拟代次测试或冷启动称为每周更新保证。

## 实机迁移验收

- 迁移后助手首屏显示礼包与乾坤问情谷，下方显示积分赛挑战券10/20、魂师、背包魂骨、宗门祈愿和至高遗迹。挂载状态为14项、generation=1。
- 迁移前后194条 `dldl_` 配置/消费journal逐项相同，没有新增、丢失或改写。
- 同进程创建disabled：助手打开时为 `disable_waiting_helper_close`；关闭后为 `disabled`，再打开是官方原生“自动收送友情点”等条目。
- 同进程解除disabled：窗口打开时 `waiting_helper_close`；关闭后重新 `installed:14`、generation=2，入口恢复。此项是实际卸载/重挂测试，不等于真实热更新。
- 发布包另验证灵魂契约不足只跳过召唤并进入宗门任务、未知魂师pending跨重挂仍保留。
