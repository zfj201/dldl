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

阶段1系统退出记录只有测试主动强停，没有新发生的异常退出。原始截图、系统记录保存在本地 `evidence/phase13/`（含账号内容，不上传）。这些观测不能证明未来版本绝无检测。

## 下一层入口

Java 层存在 `Cocos2dxRenderer.onDrawFrame` 与 `Cocos2dxLuaJavaBridge.callLuaGlobalFunctionWithString(String,String)`。计划在原渲染回调完成后调用原游戏 JNI 接口执行本地 Lua，引擎自己处理 Lua 状态与栈；先观察线程再执行无业务探针。不采用固定 RVA，不安装 native inline hook，不拦截 exit/kill。

空 native 桥只实现 JNI_OnLoad 与返回当前 tid 的 ping，不访问引擎状态。NDK r27d 取自 Google 官方下载，ZIP 完整解压通过；本地构建 arm64-v8a、Android API29、16KiB 最大页对齐。
