package com.zfj.dldlextension;

import android.app.Dialog;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.os.SystemClock;
import android.view.View;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.lang.ref.WeakReference;
import java.util.function.Supplier;

/** Observe only Huawei.showLoading's actual dialog, on its UI thread. */
final class SdkLoadingMonitor {
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Supplier<LaunchRequest> active;
    private final File output;
    private WeakReference<Dialog> dialog=new WeakReference<>(null);
    private String request="";
    private long since=-1;
    private final Runnable poll=this::sample;

    SdkLoadingMonitor(File directory,Supplier<LaunchRequest> active) {
        this.output=new File(directory,"automation/sdk-loading.tsv");this.active=active;
    }
    void shown(Dialog value) {
        handler.post(() -> {
            if (dialog.get()!=value) since=-1;
            dialog=new WeakReference<>(value);
            handler.removeCallbacks(poll);sample();
        });
    }
    void hidden() {
        handler.post(() -> {since=-1;handler.removeCallbacks(poll);sample();});
    }
    private void sample() {
        Dialog value=dialog.get();
        boolean showing=value!=null && value.isShowing();
        LaunchRequest run=active.get();
        if (run==null) {since=-1;request="";}
        else {
            if (!run.id.equals(request)) {request=run.id;since=-1;}
            View decor=showing && value.getWindow()!=null?value.getWindow().getDecorView():null;
            boolean visible=decor!=null && decor.isShown() && decor.hasWindowFocus();
            long now=SystemClock.elapsedRealtime();
            if (!visible) since=-1;else if (since<0) since=now;
            String state="v1\t"+request+"\t"+Process.myPid()+"\t"+since+"\t"+now+"\t"+(visible?"visible":"hidden")+"\n";
            try {
                File tmp=new File(output.getPath()+".tmp");
                Files.write(tmp.toPath(),state.getBytes(StandardCharsets.UTF_8));
                Files.move(tmp.toPath(),output.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
            } catch (Exception ignored) { /* no fresh evidence means no restart */ }
        }
        if (showing) handler.postDelayed(poll,500);
    }
}
