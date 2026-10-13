#include <jni.h>
#include <unistd.h>

/* 加载时只注册 JNI 版本，不查找 Lua 指针、不修改游戏 native 指令、不创建线程。 */
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)vm; (void)reserved;
    return JNI_VERSION_1_6;
}

JNIEXPORT jint JNICALL
Java_com_zfj_dldlextension_NativeBridge_ping(JNIEnv *env, jclass type) {
    (void)env; (void)type;
    return (jint)gettid();
}

/* 这里只是转接：在调用者的 GL 线程上，调用游戏已有的 Java/JNI Lua 接口。
 * Lua 状态与栈仍由游戏管理；不解密、不缓存 Lua_State，也不依赖 so 固定偏移。 */
JNIEXPORT jint JNICALL
Java_com_zfj_dldlextension_NativeBridge_callGlobal(JNIEnv *env, jclass type,
        jclass game_bridge, jstring name, jstring argument) {
    (void)type;
    if (!game_bridge || !name || !argument) return -1;
    jmethodID method = (*env)->GetStaticMethodID(env, game_bridge,
        "callLuaGlobalFunctionWithString", "(Ljava/lang/String;Ljava/lang/String;)I");
    if (!method || (*env)->ExceptionCheck(env)) return -1;
    return (*env)->CallStaticIntMethod(env, game_bridge, method, name, argument);
}
