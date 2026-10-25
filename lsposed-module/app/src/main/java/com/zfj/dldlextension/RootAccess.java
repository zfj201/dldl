package com.zfj.dldlextension;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/** KernelSU mount-master shell, with bounded commands and output. Never runs on the UI thread. */
final class RootAccess {
    static final String TARGET="com.hnzh.dldlwhjx.huawei";
    static final String BASE="/data/user/0/"+TARGET+"/files/dldl_extension/automation/";
    static String quote(String s) { return "'"+s.replace("'", "'\\''")+"'"; }
    static String run(String command) throws Exception {
        Process p=new ProcessBuilder("su","-M","-c",command).redirectErrorStream(true).start();
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        Thread reader=new Thread(() -> {
            try { byte[] b=new byte[4096];int n;
                while ((n=p.getInputStream().read(b))!=-1) {
                    synchronized(out) { if (out.size()+n>65536) {p.destroyForcibly();return;} out.write(b,0,n); }
                }
            } catch (Exception ignored) { /* caller checks exit code/timeout */ }
        },"dldl-root-output");
        reader.setDaemon(true);reader.start();
        if (!p.waitFor(20,TimeUnit.SECONDS)) {p.destroyForcibly();throw new IllegalStateException("Root 命令超时");}
        reader.join(1000);
        String result; synchronized(out) {result=out.toString(StandardCharsets.UTF_8.name());}
        if (p.exitValue()!=0) throw new IllegalStateException("Root 操作失败："+result);
        return result;
    }
    static String read(String name) throws Exception {
        return run("if [ -f "+quote(BASE+name)+" ]; then head -c 4096 "+quote(BASE+name)+"; fi");
    }
    private static String promotionGuard(String id,long expires) {
        if (!id.matches("[A-Za-z0-9_-]{1,80}") || expires<=0) throw new IllegalArgumentException("Invalid promotion request");
        return "if [ $(date +%s) -gt "+expires+" ] || [ -f "+quote(BASE+"../disabled")+" ]"
            +" || ! grep -q "+quote("^v1\t"+id+"\t")+" "+quote(BASE+"launch.tsv")
            +" || { [ -f "+quote(BASE+"cancel.tsv")+" ] && grep -qx "+quote(id)+" "+quote(BASE+"cancel.tsv")
            +"; }; then exit 0; fi; ";
    }
    static String promotionSnapshot(String id,long expires,String temp) throws Exception {
        return run(promotionGuard(id,expires)
            +"focus=$(dumpsys window | grep mCurrentFocus | sed 's/^ *//'); case \"$focus\" in *"
            +quote(" u0 "+HuaweiPromotion.COMPONENT+"}")+"*) ;; *) exit 0;; esac; "
            +"printf '%s\\n' \"$focus\"; dumpsys activity top | grep -E '^TASK |^  ACTIVITY '; "
            +"uiautomator dump --compressed "+quote(temp)+" >/dev/null 2>&1 && head -c 32769 "+quote(temp)
            +"; rm -f "+quote(temp));
    }
    static String closePromotion(String id,long expires,HuaweiPromotion.Target target) throws Exception {
        return run(promotionGuard(id,expires)
            +"focus=$(dumpsys window | grep mCurrentFocus | sed 's/^ *//'); "
            +"if [ \"$focus\" != "+quote(target.focus)+" ]; then echo window_changed; exit 0; fi; "
            +"input tap "+target.x+" "+target.y+" && echo promotion_close_sent");
    }
    static String restartLoading(String id,String pid,String since,String status) throws Exception {
        if (!id.matches("[A-Za-z0-9_-]{1,80}") || !pid.matches("[0-9]+") || !since.matches("[0-9]+"))
            throw new IllegalArgumentException("Invalid recovery request");
        // Re-check immediately before stopping: a later login/queue transition must win.
        String prefix="v1\t"+id+"\t";
        return run("if [ \"$(pidof "+TARGET+")\" != "+quote(pid)+" ]; then echo process_changed; exit 0; fi; "
            +"if ! dumpsys window | grep mCurrentFocus | grep -q "+quote(TARGET)
            +"; then echo not_foreground; exit 0; fi; "
            +"if ! grep -q "+quote("^"+prefix+pid+"\t"+since+"\t[0-9]*\tvisible$")+" "+quote(BASE+"sdk-loading.tsv")
            +"; then echo loading_changed; exit 0; fi; "
            +"task_status=$(cat "+quote(BASE+"startup.tsv")+" 2>/dev/null); "
            +"if [ \"$task_status\" != "+quote(status.trim())+" ]; then echo state_changed; exit 0; fi; "
            +"if [ -f "+quote(BASE+"request.tsv")+" ] && grep -q "+quote("^"+prefix)+" "+quote(BASE+"request.tsv")
            +"; then echo helper_requested; exit 0; fi; "
            +"if [ -f "+quote(BASE+"cancel.tsv")+" ] && grep -qx "+quote(id)+" "+quote(BASE+"cancel.tsv")
            +"; then echo cancelled; exit 0; fi; "
            +"am force-stop "+TARGET+" && rm -f "+quote(BASE+"sdk-loading.tsv")
            +" && echo restarted && am start -n "+TARGET+"/com.game.sdk.GameSdkActivity");
    }
    static void write(String name,String text) throws Exception {
        String encoded=android.util.Base64.encodeToString(text.getBytes(StandardCharsets.UTF_8),android.util.Base64.NO_WRAP);
        String tmp=quote(BASE+name+".tmp"), path=quote(BASE+name);
        run("task_uid=$(stat -c %u "+quote("/data/user/0/"+TARGET)+") && mkdir -p "+quote(BASE)
            +" && chown \"$task_uid:$task_uid\" "+quote(BASE)+" && chmod 700 "+quote(BASE)
            +" && printf %s "+quote(encoded)+" | base64 -d > "+tmp
            +" && chown \"$task_uid:$task_uid\" "+tmp+" && chmod 600 "+tmp
            +" && restorecon "+tmp+" && mv "+tmp+" "+path);
    }
    private RootAccess() {}
}
