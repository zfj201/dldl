package com.zfj.dldlextension;

final class NativeBridge {
    static void load() { System.loadLibrary("dldl_bridge"); }
    static native int ping();
    static native int callGlobal(Class<?> gameBridge, String name, String argument);
    private NativeBridge() {}
}
