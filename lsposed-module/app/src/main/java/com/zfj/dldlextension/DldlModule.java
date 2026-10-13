package com.zfj.dldlextension;

import android.os.Process;
import android.util.Log;
import java.io.File;
import java.io.FileWriter;
import io.github.libxposed.api.XposedModule;

/** Stage 1 has no hooks, native loads, Lua access or protocol calls. */
public final class DldlModule extends XposedModule {
    private static final String TARGET = "com.hnzh.dldlwhjx.huawei";
    private boolean mainProcess;
    @Override public void onModuleLoaded(ModuleLoadedParam param) {
        mainProcess = TARGET.equals(param.getProcessName());
    }
    @Override public void onPackageLoaded(PackageLoadedParam param) {
        if (!mainProcess || !TARGET.equals(param.getPackageName()) || !param.isFirstPackage()) return;
        try {
            File directory = new File(param.getApplicationInfo().dataDir, "files/dldl_extension");
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IllegalStateException("Cannot create extension directory");
            String event = "stage=" + BuildConfig.PROBE_STAGE + " event=java_ready pid=" + Process.myPid()
                + " tid=" + Process.myTid() + " time=" + System.currentTimeMillis();
            try (FileWriter writer = new FileWriter(new File(directory, "loader.log"), true)) { writer.write(event + "\n"); }
            log(Log.INFO, "DldlExtension", event);
        } catch (Throwable error) {
            log(Log.ERROR, "DldlExtension", "Probe initialization failed", error);
        }
    }
}
