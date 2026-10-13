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
