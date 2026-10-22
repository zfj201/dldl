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
