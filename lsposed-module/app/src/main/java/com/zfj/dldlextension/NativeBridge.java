package com.zfj.dldlextension;

final class NativeBridge {
    static void load() { System.loadLibrary("dldl_bridge"); }
    static native int ping();
    private NativeBridge() {}
}
