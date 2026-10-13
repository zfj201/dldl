package com.zfj.dldlextension;

import android.os.Process;
import android.util.Log;
import java.io.File;
import java.io.FileWriter;
import java.lang.reflect.Method;
import java.lang.reflect.Field;
import android.os.SystemClock;
import io.github.libxposed.api.XposedModule;
import io.github.libxposed.api.XposedInterface;

/** Staged probe. Original game methods always complete before our callback. */
public final class DldlModule extends XposedModule {
    private static final String TARGET = "com.hnzh.dldlwhjx.huawei";
    private boolean mainProcess;
    private boolean nativeReady;
    private File directory;

    @Override public void onModuleLoaded(ModuleLoadedParam param) {
        mainProcess = TARGET.equals(param.getProcessName());
    }

    private void record(String event) {
        String line = "stage=" + BuildConfig.PROBE_STAGE + " event=" + event + " pid=" + Process.myPid()
            + " tid=" + Process.myTid() + " time=" + System.currentTimeMillis();
        try (FileWriter writer = new FileWriter(new File(directory, "loader.log"), true)) {
            writer.write(line + "\n");
        } catch (Exception error) { log(Log.ERROR, "DldlExtension", "Cannot record probe", error); }
        log(Log.INFO, "DldlExtension", line);
    }

    @Override public void onPackageLoaded(PackageLoadedParam param) {
        if (!mainProcess || !TARGET.equals(param.getPackageName()) || !param.isFirstPackage()) return;
        try {
            directory = new File(param.getApplicationInfo().dataDir, "files/dldl_extension");
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IllegalStateException("Cannot create extension directory");
            record("java_ready");
            if (BuildConfig.PROBE_STAGE >= 2) {
                NativeBridge.load();
                if (NativeBridge.ping() != Process.myTid()) throw new IllegalStateException("Native thread mismatch");
                nativeReady = true;
                record("native_ready");
            }
        } catch (Throwable error) { record("initialization_failed:" + error); }
    }

    @Override public void onPackageReady(PackageReadyParam param) {
        if (!mainProcess || !TARGET.equals(param.getPackageName()) || !param.isFirstPackage()
                || BuildConfig.PROBE_STAGE < 3 || !nativeReady) return;
        try {
            Class<?> renderer = param.getClassLoader().loadClass("org.cocos2dx.lib.Cocos2dxRenderer");
            Method draw = renderer.getDeclaredMethod("onDrawFrame", javax.microedition.khronos.opengles.GL10.class);
            Field initialized = renderer.getDeclaredField("mNativeInitCompleted");
            initialized.setAccessible(true);
            Class<?> gameBridge = param.getClassLoader().loadClass("org.cocos2dx.lib.Cocos2dxLuaJavaBridge");
            File probe = new File(directory, "probe.lua");
            if (BuildConfig.PROBE_STAGE >= 4) {
                String output = new File(directory, "lua_probe.log").getAbsolutePath();
                try (FileWriter writer = new FileWriter(probe)) {
                    writer.write("local f=assert(io.open('" + output + "','a')); "
                        + "f:write('lua_ready pid=" + Process.myPid() + " time=',tostring(os.time()),' state=',tostring(_G),'\\n');f:close();return 0\n");
                }
            }
            hook(draw).intercept(new XposedInterface.Hooker() {
                private boolean observed;
                private boolean called;
                private long readyAt;
                @Override public Object intercept(XposedInterface.Chain chain) throws Throwable {
                    Object result = chain.proceed();
                    try {
                        if (!observed) {
                            observed = true;
                            readyAt = SystemClock.elapsedRealtime() + 2000;
                            record("render_observed:thread=" + Thread.currentThread().getName() + ":native_tid=" + NativeBridge.ping());
                        }
                        if (BuildConfig.PROBE_STAGE >= 4 && !called && SystemClock.elapsedRealtime() >= readyAt
                                && initialized.getBoolean(chain.getThisObject())) {
                            called = true;
                            record("lua_probe_begin");
                            int value = NativeBridge.callGlobal(gameBridge, "dofile", probe.getAbsolutePath());
                            record("lua_probe_return:value=" + value);
                        }
                    } catch (Throwable error) { called = true; record("render_probe_failed:" + error); }
                    return result;
                }
            });
            record("render_hook_ready");
        } catch (Throwable error) { record("render_hook_failed:" + error); }
    }
}
