package com.zfj.dldlextension;

import android.os.Process;
import android.util.Log;
import java.io.File;
import java.io.FileWriter;
import java.lang.reflect.Method;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import android.os.SystemClock;
import io.github.libxposed.api.XposedModule;
import io.github.libxposed.api.XposedInterface;

/** LSPosed 加载入口：阶段5挂载独立 Lua 扩展；阶段1～4保留作分层接入诊断。 */
public final class DldlModule extends XposedModule {
    private static final String TARGET = "com.hnzh.dldlwhjx.huawei";
    private boolean mainProcess;
    private boolean nativeReady;
    private File directory;
    private File bootstrap;

    private boolean startupActive() {
        if (directory == null || new File(directory, "disabled").exists()) return false;
        try {
            File f=new File(directory,"automation/launch.tsv");
            if (!f.isFile() || f.length()>512) return false;
            LaunchRequest r=LaunchRequest.parse(new String(Files.readAllBytes(f.toPath()),StandardCharsets.UTF_8),System.currentTimeMillis()/1000);
            if (r==null) return false;
            File cancel=new File(directory,"automation/cancel.tsv");
            if (cancel.isFile() && new String(Files.readAllBytes(cancel.toPath()),StandardCharsets.UTF_8).equals(r.id+"\n")) return false;
            File status=new File(directory,"automation/startup.tsv");
            if (status.isFile() && status.length()<2048) {
                String[] p=new String(Files.readAllBytes(status.toPath()),StandardCharsets.UTF_8).split("\t");
                if (p.length>2 && p[1].equals(r.id) && !p[2].equals("waiting") && !p[2].equals("entering")) return false;
            }
            return true;
        } catch (Exception e) { return false; }
    }

    private void installSdkHooks(ClassLoader loader) {
        // Only these SDK notice responses carry the optional Huawei promotion Intent.
        // Returning no notice leaves login, identity verification and payment callbacks intact.
        for (String name : new String[]{"com.huawei.hms.support.api.entity.core.JosGetNoticeResp",
                "com.huawei.hms.support.api.entity.game.GameNoticeResp"}) {
            try {
                Method notice=loader.loadClass(name).getDeclaredMethod("getNoticeIntent");
                hook(notice).intercept(chain -> {
                    if (startupActive()) { record("sdk_promotion_suppressed:"+name); return null; }
                    return chain.proceed();
                });
                record("sdk_notice_hook_ready:"+name);
            } catch (Throwable e) { record("sdk_notice_hook_unavailable:"+name+":"+e); }
        }
        try {
            Class<?> activity=loader.loadClass("com.huawei.updatesdk.service.otaupdate.AppUpdateActivity");
            Class<?> info=loader.loadClass("com.huawei.updatesdk.service.appmgr.bean.ApkUpgradeInfo");
            Method show=activity.getDeclaredMethod("c",info);
            Method compulsory=info.getMethod("getIsCompulsoryUpdate_");
            Field must=activity.getDeclaredField("g"), status=activity.getDeclaredField("m"), button=activity.getDeclaredField("o");
            must.setAccessible(true);status.setAccessible(true);button.setAccessible(true);
            hook(show).intercept(chain -> {
                if (startupActive() && chain.getArg(0)!=null) {
                    Object a=chain.getThisObject();
                    if (((Number)compulsory.invoke(chain.getArg(0))).intValue()==0 && !must.getBoolean(a)) {
                        // Match SDK cancel status (m=4, o=100), then run its finish() notification.
                        status.setInt(a,4);button.setInt(a,100);
                        ((android.app.Activity)a).finish();
                        record("optional_apk_update_cancelled");return null;
                    }
                    Files.write(new File(directory,"automation/java-block.tsv").toPath(),"required_update\n".getBytes(StandardCharsets.UTF_8));
                    record("required_apk_update_waiting_user");
                }
                return chain.proceed();
            });
            record("sdk_update_hook_ready");
        } catch (Throwable e) { record("sdk_update_hook_unavailable:"+e); }
    }

    @Override public void onModuleLoaded(ModuleLoadedParam param) {
        // 只在游戏主进程工作，避免在 SDK/服务子进程重复加载。
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
            // 扩展使用独立目录；不写官方 game_start 或游戏热更新资源目录。
            directory = new File(param.getApplicationInfo().dataDir, "files/dldl_extension");
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IllegalStateException("Cannot create extension directory");
            File automation = new File(directory, "automation");
            if (!automation.isDirectory() && !automation.mkdirs()) throw new IllegalStateException("Cannot create automation directory");
            record("java_ready");
            if (BuildConfig.PROBE_STAGE >= 2) {
                if (BuildConfig.PROBE_STAGE >= 5) PayloadStore.verifyNative(getModuleApplicationInfo().sourceDir);
                NativeBridge.load();
                if (NativeBridge.ping() != Process.myTid()) throw new IllegalStateException("Native thread mismatch");
                nativeReady = true;
                record("native_ready");
                if (BuildConfig.PROBE_STAGE >= 5) {
                    bootstrap = PayloadStore.prepare(getModuleApplicationInfo().sourceDir, directory);
                    record("payload_ready:" + bootstrap.getParentFile().getName());
                }
            }
        } catch (Throwable error) { record("initialization_failed:" + error); }
    }

    @Override public void onPackageReady(PackageReadyParam param) {
        if (!mainProcess || !TARGET.equals(param.getPackageName()) || !param.isFirstPackage()
                || BuildConfig.PROBE_STAGE < 3 || !nativeReady) return;
        try {
            if (BuildConfig.PROBE_STAGE >= 5) installSdkHooks(param.getClassLoader());
            Class<?> renderer = param.getClassLoader().loadClass("org.cocos2dx.lib.Cocos2dxRenderer");
            Method draw = renderer.getDeclaredMethod("onDrawFrame", javax.microedition.khronos.opengles.GL10.class);
            // 引擎初始化是第一道门槛；Lua 引导器还会等待业务控制器和助手列表就绪。
            Field initialized = renderer.getDeclaredField("mNativeInitCompleted");
            initialized.setAccessible(true);
            Class<?> gameBridge = param.getClassLoader().loadClass("org.cocos2dx.lib.Cocos2dxLuaJavaBridge");
            File probe = new File(directory, "probe.lua");
            if (BuildConfig.PROBE_STAGE == 4) {
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
                private long nextTick;
                private int lastResult = Integer.MIN_VALUE;
                @Override public Object intercept(XposedInterface.Chain chain) throws Throwable {
                    // 原渲染必须先完成，且其异常不能被扩展的 catch 吞掉。
                    // 借用游戏的 GL 线程调用 Lua，不能换到自行创建的后台线程。
                    Object result = chain.proceed();
                    try {
                        if (!observed) {
                            observed = true;
                            readyAt = SystemClock.elapsedRealtime() + 2000;
                            record("render_observed:thread=" + Thread.currentThread().getName() + ":native_tid=" + NativeBridge.ping());
                        }
                        if (BuildConfig.PROBE_STAGE == 4 && !called && SystemClock.elapsedRealtime() >= readyAt
                                && initialized.getBoolean(chain.getThisObject())) {
                            called = true;
                            record("lua_probe_begin");
                            int value = NativeBridge.callGlobal(gameBridge, "dofile", probe.getAbsolutePath());
                            record("lua_probe_return:value=" + value);
                        }
                        if (BuildConfig.PROBE_STAGE >= 5 && bootstrap != null && !called
                                && SystemClock.elapsedRealtime() >= nextTick && initialized.getBoolean(chain.getThisObject())) {
                            // 每秒只检查是否需要挂载；已挂载时 Lua 立即返回，不会每秒执行日常任务。
                            nextTick = SystemClock.elapsedRealtime() + 1000;
                            int value = NativeBridge.callGlobal(gameBridge, "dofile", bootstrap.getAbsolutePath());
                            if (value != lastResult) { lastResult = value; record("loader_result:value=" + value); }
                        }
                    // 扩展侧 Java 异常停止后续尝试，保留本帧原结果；此处不能拦截 native 内存崩溃。
                    } catch (Throwable error) { called = true; record("render_probe_failed:" + error); }
                    return result;
                }
            });
            record("render_hook_ready");
        } catch (Throwable error) { record("render_hook_failed:" + error); }
    }
}
