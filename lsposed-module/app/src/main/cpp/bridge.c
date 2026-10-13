#include <jni.h>
#include <unistd.h>

/* No Lua pointers, fixed offsets, inline hooks or native worker threads. */
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)vm; (void)reserved;
    return JNI_VERSION_1_6;
}

JNIEXPORT jint JNICALL
Java_com_zfj_dldlextension_NativeBridge_ping(JNIEnv *env, jclass type) {
    (void)env; (void)type;
    return (jint)gettid();
}

/* The engine owns its Lua state and stack. Invoke its public JNI contract on
 * the calling GL thread; never cache a Lua_State or resolve private offsets. */
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
