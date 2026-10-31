package com.zfj.dldlextension;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.os.SystemClock;
import android.view.View;
import java.io.File;
import java.lang.ref.WeakReference;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.function.Supplier;

/** GL reports the exact sprite; the UI thread owns window visibility and the external-service sample. */
final class StartupSplashMonitor {
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Supplier<LaunchRequest> active;
    private final File output;
    private SplashVisibility visibility=new SplashVisibility();
    private WeakReference<Activity> activity=new WeakReference<>(null);
    private volatile Observation observation=new Observation("",false,0);
    private final Runnable poll=this::sample;

    private static final class Observation {
        final String id;
        final boolean visible;
        final long time;
        Observation(String id,boolean visible,long time) {this.id=id;this.visible=visible;this.time=time;}
    }
    StartupSplashMonitor(File directory,Supplier<LaunchRequest> active) {
        this.active=active;output=new File(directory,"automation/startup-splash.tsv");
    }
    void attach(Activity value) {
        // Called on the activity thread before onCreate; don't wait for SDK initialization.
        if (activity.get()!=value) {activity=new WeakReference<>(value);visibility=new SplashVisibility();}
        handler.removeCallbacks(poll);handler.post(poll);
    }
    void observed(String id,boolean visible) {
        observation=new Observation(id,visible,SystemClock.elapsedRealtime());
    }
    private void sample() {
        Activity a=activity.get();
        LaunchRequest run=active.get();
        View decor=a!=null && !a.isFinishing() && !a.isDestroyed() && a.getWindow()!=null
            ?a.getWindow().peekDecorView():null;
        boolean focused=decor!=null && decor.isShown() && decor.hasWindowFocus();
        long now=SystemClock.elapsedRealtime();
        Observation seen=observation;
        long since=visibility.update(run==null?"":run.id,focused,seen.id,seen.visible,seen.time,now);
        if (run!=null) {
            String state="v1\t"+run.id+"\t"+Process.myPid()+"\t"+since+"\t"+now+"\t"+(since>=0?"visible":"hidden")+"\n";
            try {
                File tmp=new File(output.getPath()+".tmp");
                Files.write(tmp.toPath(),state.getBytes(StandardCharsets.UTF_8));
                Files.move(tmp.toPath(),output.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
            } catch (Exception ignored) { /* The service also verifies identity, progress and current window. */ }
        }
        if (a!=null && !a.isDestroyed()) handler.postDelayed(poll,500);
    }
}
