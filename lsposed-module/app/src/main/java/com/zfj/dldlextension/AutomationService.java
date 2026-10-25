package com.zfj.dldlextension;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.SystemClock;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

/** App-owned wakeup/Root launch; the LSPosed side owns all SDK and game actions. */
public final class AutomationService extends Service {
    private final AtomicBoolean running=new AtomicBoolean();
    private volatile boolean cancelled;
    private PowerManager.WakeLock wake;
    private static final String CHANNEL="daily_automation";
    @Override public IBinder onBind(Intent intent) {return null;}
    private void update(String status) {
        DailySchedule.prefs(this).edit().putString("status",status).apply();
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,AutomationService.class).setAction("cancel"),
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification n=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_popup_sync)
            .setContentTitle("香香小助手自动运行").setContentText(status).setContentIntent(open)
            .addAction(new Notification.Action.Builder(null,"停止",stop).build()).setOngoing(running.get()).build();
        startForeground(7,n);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        getSystemService(NotificationManager.class).createNotificationChannel(
            new NotificationChannel(CHANNEL,"每日助手",NotificationManager.IMPORTANCE_LOW));
        if (intent==null) {stopSelf();return START_NOT_STICKY;}
        if ("cancel".equals(intent.getAction())) {cancelled=true;if (!running.get()) stopSelf();return START_NOT_STICKY;}
        if (!running.compareAndSet(false,true)) return START_NOT_STICKY;
        cancelled=false;update("正在准备启动游戏");
        String mode="verify".equals(intent.getAction())?"verify":"run_all";
        wake=getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"dldl:automation");
        wake.acquire(40*60*1000L);
        new Thread(() -> execute(mode),"dldl-automation").start();
        return START_NOT_STICKY;
    }
    private void execute(String mode) {
        String id="lsposed-"+UUID.randomUUID();
        boolean published=false;
        try {
            SharedPreferences prefs=DailySchedule.prefs(this);
            String rid=prefs.getString("rid",""),server=prefs.getString("server","");
            if (!rid.matches("[A-Za-z0-9_-]+") || !server.matches("[A-Za-z0-9_-]+"))
                throw new IllegalStateException("请先登录主城并绑定角色");
            long now=System.currentTimeMillis()/1000;
            RootAccess.run("id -u");
            // Clear only transport state, never the daily completion/consumption journal.
            RootAccess.run("rm -f "+RootAccess.quote(RootAccess.BASE+"java-block.tsv")+" "+RootAccess.quote(RootAccess.BASE+"cancel.tsv")
                +" "+RootAccess.quote(RootAccess.BASE+"sdk-loading.tsv"));
            RootAccess.write("launch.tsv","v1\t"+id+"\t"+rid+"\t"+server+"\t"+now+"\t"+(now+300)+"\t"+mode+"\n");
            published=true;
            String launchOutput=RootAccess.run("input keyevent KEYCODE_WAKEUP; wm dismiss-keyguard; am start -W -n "
                +RootAccess.TARGET+"/com.game.sdk.GameSdkActivity");
            Files.write(new File(getFilesDir(),"last-launch.txt").toPath(),launchOutput.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            long deadline=SystemClock.elapsedRealtime()+36*60*1000L;
            LoadingRecovery recovery=new LoadingRecovery();
            long nextPromotion=0;
            int promotionCloses=0;
            String last="";
            while (SystemClock.elapsedRealtime()<deadline) {
                if (cancelled) {RootAccess.write("cancel.tsv",id+"\n");update("已停止；未确认的助手执行不会自动重跑");return;}
                String status=RootAccess.read("startup.tsv");
                String[] parts=status.trim().split("\t");
                if (parts.length>=5 && parts[1].equals(id)) {
                    String current=parts[2]+" / "+parts[3];
                    if (!current.equals(last)) {last=current;update(current);}
                    if (parts[2].matches("verified|completed|already_completed|blocked|failed|uncertain|rejected|cancelled")) {
                        Files.write(new File(getFilesDir(),"last-startup.tsv").toPath(),status.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                        if (parts[2].equals("completed") || parts[2].equals("already_completed")) {
                            Files.write(new File(getFilesDir(),"last-tasks.tsv").toPath(),RootAccess.read("tasks.tsv").getBytes(java.nio.charset.StandardCharsets.UTF_8));
                            if (prefs.getBoolean("close_game",true)) RootAccess.run("am force-stop "+RootAccess.TARGET);
                        }
                        return;
                    }
                } else if (System.currentTimeMillis()/1000>now+320) {
                    throw new IllegalStateException("启动超时：请检查 LSPosed 作用域、锁屏、SDK 登录或加载器日志");
                }
                if (SystemClock.elapsedRealtime()>=nextPromotion && System.currentTimeMillis()/1000<=now+300
                        && promotionCloses<6 && !cancelled) {
                    nextPromotion=SystemClock.elapsedRealtime()+3000;
                    try {
                        HuaweiPromotion.Target promotion=HuaweiPromotion.find(RootAccess.promotionSnapshot(id,now+300,
                            new File(getCacheDir(),"huawei-promotion.xml").getAbsolutePath()));
                        if (promotion!=null && !cancelled) {
                            String closed=RootAccess.closePromotion(id,now+300,promotion).trim();
                            if (closed.equals("promotion_close_sent")) promotionCloses++;
                            try (FileWriter log=new FileWriter(new File(getFilesDir(),"promotion-close.log"),true)) {
                                log.write(System.currentTimeMillis()+"\t"+id+"\t"+closed+"\n");
                            }
                        }
                    } catch (Exception e) {
                        // Optional close must not interrupt loading recovery or the startup timeout.
                        android.util.Log.w("DldlExtension","Promotion inspection failed",e);
                    }
                }
                if (!recovery.observing(id,status)) {Thread.sleep(2000);continue;}
                String loading=RootAccess.read("sdk-loading.tsv");
                LoadingRecovery.Decision decision=recovery.inspect(loading,id,status,SystemClock.elapsedRealtime());
                if (decision==LoadingRecovery.Decision.EXHAUSTED) {
                    String stopped="v1\t"+id+"\tblocked\tsdk_loading_retry_exhausted\t"+System.currentTimeMillis()/1000+"\n";
                    RootAccess.write("startup.tsv",stopped);
                    Files.write(new File(getFilesDir(),"last-startup.tsv").toPath(),stopped.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                    throw new IllegalStateException("华为启动加载连续卡住，已重启3次，请检查网络或SDK登录");
                }
                if (decision==LoadingRecovery.Decision.RESTART && !cancelled) {
                    String[] observed=loading.trim().split("\t");
                    String pid=observed[2];
                    String result=RootAccess.restartLoading(id,pid,observed[3],status);
                    if (result.startsWith("restarted")) recovery.restarted();
                    try (FileWriter log=new FileWriter(new File(getFilesDir(),"loading-recovery.log"),true)) {
                        log.write(System.currentTimeMillis()+"\t"+id+"\t"+pid+"\t"+recovery.restarts()+"\t"+result.replace('\n',' ')+"\n");
                    }
                    if (result.startsWith("restarted")) update("启动加载超过15秒，已重启游戏（"+recovery.restarts()+"/3）");
                }
                Thread.sleep(1000);
            }
            RootAccess.write("cancel.tsv",id+"\n");
            throw new IllegalStateException("执行等待超时，结果未确认，请查看游戏");
        } catch (Exception e) {
            if (published) try {RootAccess.write("cancel.tsv",id+"\n");} catch (Exception ignored) { /* preserve original error */ }
            update("运行停止："+e.getMessage());
        } finally {
            if (published) try {
                String current=RootAccess.read("launch.tsv");
                if (current.startsWith("v1\t"+id+"\t")) RootAccess.run("rm -f "+RootAccess.quote(RootAccess.BASE+"launch.tsv"));
            } catch (Exception ignored) { /* expired launch files cannot initiate a later run */ }
            if (wake!=null && wake.isHeld()) wake.release();
            running.set(false);stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();
        }
    }
}
