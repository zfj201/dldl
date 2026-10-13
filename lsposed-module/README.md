# 香香小助手扩展

独立 Android Studio 项目，位于 `zfj201/dldl` 仓库的 `lsposed-module/`。现代 libxposed API 102，Android 10+、arm64。仅作用于 `com.hnzh.dldlwhjx.huawei` 主进程。

## 工作方式

LSPosed 在进程启动时加载小型 JNI 桥，在 `Cocos2dxRenderer.onDrawFrame` 原方法结束后，每秒一次调用游戏已有的 `Cocos2dxLuaJavaBridge.callLuaGlobalFunctionWithString`。通过 `dofile` 执行独立引导器，不使用固定 RVA、Lua_State 指针或 native inline hook。渲染尚未初始化则不调用。

官方 `game_start` 完成后安装 14 项入口；不自动执行任务。控制器、窗口类、配置列表或 beginGame 对象变化时重新挂载；同一代次不重复安装。安装失败回滚自己已改动的方法；不清配置或消费 journal。历史单笔修复入口不进入发布包。

native 和 Lua SHA-256 来自签名 APK 内资源。复制到游戏 `files/dldl_extension/bundle-<hash>/`，逐文件校验并原子替换。冷启动会恢复缺失或损坏的副本。官方资源哈希不作为长期启动门槛，也不会被模块覆盖。

## 构建

Android Studio JDK 21、SDK 37、NDK r27d。`local.properties` 指定 `sdk.dir`、`ndk.dir`，或用 `ANDROID_NDK_HOME` 指定 NDK；本地配置不提交。NDK 构建脚本当前适配 macOS。

```sh
./gradlew :app:assembleDebug :app:lintDebug
```

Gradle 自动构建 JNI 桥、生成独立 Lua 包及 manifest。开发 APK 位于 `app/build/outputs/apk/debug/app-debug.apk`，默认阶段5。`-PprobeStage=1/2/3/4` 可分别构建 Java、空 native、渲染观察、单次 Lua 探针。阶段2/3不会调用新增 native 执行函数。

```sh
PYTHONPATH=.tools python3 tests/test_extension_loader.py
```

上述测试从仓库根目录运行，依赖本机 Lua 5.1/Lupa 与已恢复游戏类，包含已有111项回归及加载器生命周期检查，不调用设备或网络。

## 使用与回退

在 LSPosed 中启用模块、仅勾选游戏，重启游戏。打开游戏内香香小助手，在日常页设置与执行。停用模块并重启游戏即可回到官方助手；消费 journal 与偏好保留。

旧 `game_start` 组合包必须先按当前资源版本精确迁移。发现 `DLDL_DAILY_GIFTS` 或相同自定义 ID 时，模块拒绝重复安装。不要把旧官方备份复制到已更新的游戏。

诊断：`files/dldl_extension/loader.log`，对应 bundle 下的 `status.txt` / `status.log`。创建 `files/dldl_extension/disabled` 可暂停挂载；已打开助手则等其关闭再卸载。移除此文件恢复挂载。通常直接使用 LSPosed 总开关即可。

APK 为本机开发签名；更新须保持签名密钥。正式发布应配置专用签名，密钥与密码不得提交 Git。没有在线代码下载。

## 实测边界

阶段进展与实际证据见 `reports/19_LSPosed自动挂载验证与开发.md`。业务函数、Java JNI 接口、ABI、框架或初始化流程变化时仍可能失效。真实 APK 覆盖升级及热更新尚未完成验收，不保证所有未来版本。
