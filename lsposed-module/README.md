# DldlExtension

独立 Android Studio 项目，位于 zfj201/dldl 仓库的 `lsposed-module/`，使用现代 libxposed API 102。

初始阶段仅在目标主进程写入本地标记，不安装 hook、不加载业务、不发送游戏请求。

## 构建

使用 Android Studio 的 JDK 与已安装 Android SDK 37：

```sh
./gradlew :app:assembleDebug -PprobeStage=1
```

产物：`app/build/outputs/apk/debug/app-debug.apk`。
作用域只允许 `com.hnzh.dldlwhjx.huawei`。日志位于游戏私有目录 `files/dldl_extension/loader.log`。

分层验收依据上级项目 `reports/17_更新后自动挂载架构建议.md`。每层记录实际启动和退出证据，未经验证不得宣称支持所有未来更新。
