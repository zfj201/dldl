package com.zfj.dldlextension;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private LinearLayout layout;
    private TextView status;
    private EditText rid,server;
    private SharedPreferences prefs;
    private void button(String text,Runnable action) {
        Button b=new Button(this);b.setText(text);b.setOnClickListener(v -> action.run());layout.addView(b);
    }
    private void message(String text) {Toast.makeText(this,text,Toast.LENGTH_LONG).show();}
    private boolean saveRole() {
        String r=rid.getText().toString().trim(),s=server.getText().toString().trim();
        if (!r.matches("[A-Za-z0-9_-]+") || !s.matches("[A-Za-z0-9_-]+")) {message("请先绑定或填写角色与服务器 ID");return false;}
        prefs.edit().putString("rid",r).putString("server",s).apply();return true;
    }
    private void start(String mode) {
        if (saveRole()) startForegroundService(new Intent(this,AutomationService.class).setAction(mode));
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);prefs=DailySchedule.prefs(this);
        ScrollView scroll=new ScrollView(this);scroll.setFitsSystemWindows(true);layout=new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(32,48,32,40);scroll.addView(layout);
        TextView text=new TextView(this);text.setTextSize(18);
        text.setText("香香小助手扩展 "+BuildConfig.VERSION_NAME
            +"\n\n在 LSPosed 中启用模块，仅勾选斗罗大陆，然后重启游戏。"
            +"\n\n自动运行会处理已识别的启动更新和推广公告，开始冒险，进入主城后执行已开启的助手完整列表。同一角色每天仅完成一次。"
            +"\n\n需要 Root 授权、精确闹钟与允许后台运行。普通手动打开游戏不会触发自动执行。");layout.addView(text);
        rid=new EditText(this);rid.setSingleLine();rid.setHint("角色 ID");rid.setText(prefs.getString("rid",""));layout.addView(rid);
        server=new EditText(this);server.setSingleLine();server.setHint("服务器 ID");server.setText(prefs.getString("server",""));layout.addView(server);
        button("绑定当前角色（先手动进入主城）",() -> new Thread(() -> {
            try {
                String[] p=RootAccess.read("ready.tsv").trim().split("\t");
                long now=System.currentTimeMillis()/1000;
                if (p.length!=6 || !p[1].equals("ready") || now-Long.parseLong(p[5])>60 || now<Long.parseLong(p[5])-5)
                    throw new IllegalStateException("未读取到最近一分钟的主城就绪信息，请先打开游戏进入主城");
                runOnUiThread(() -> {rid.setText(p[2]);server.setText(p[3]);saveRole();message("已绑定当前角色");});
            } catch(Exception e) {runOnUiThread(() -> message(e.getMessage()));}
        },"dldl-bind-role").start());
        button("保存角色绑定",() -> {if(saveRole()) message("已保存");});
        CheckBox close=new CheckBox(this);close.setText("助手完成后关闭游戏");close.setChecked(prefs.getBoolean("close_game",true));
        close.setOnCheckedChangeListener((b,on) -> prefs.edit().putBoolean("close_game",on).apply());layout.addView(close);
        CheckBox daily=new CheckBox(this);daily.setText("每天北京时间 07:00 自动运行");daily.setChecked(prefs.getBoolean("scheduled",false));
        daily.setOnCheckedChangeListener((b,on) -> {
            if (on && !saveRole()) {daily.setChecked(false);return;}
            if (on && !DailySchedule.permitted(this)) {
                daily.setChecked(false);startActivity(new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,Uri.parse("package:"+getPackageName())));
                message("允许精确闹钟后，返回开启每日运行");return;
            }
            prefs.edit().putBoolean("scheduled",on).apply();DailySchedule.arm(this);
        });layout.addView(daily);
        button("允许后台运行",() -> startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)));
        if (android.os.Build.VERSION.SDK_INT>=33) button("允许运行通知",() -> requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},1));
        button("仅验证启动（不执行任务）",() -> start("verify"));
        button("30秒后验证定时启动（不执行任务）",() -> {
            if (saveRole()) try {DailySchedule.verifyIn30Seconds(this);message("30秒后验证定时启动，可返回桌面或关闭屏幕");}
            catch (Exception e) {message(e.getMessage());}
        });
        button("立即运行完整助手",() -> start("run_all"));
        button("停止自动运行",() -> startService(new Intent(this,AutomationService.class).setAction("cancel")));
        button("打开游戏",() -> {
            Intent launch=getPackageManager().getLaunchIntentForPackage(RootAccess.TARGET);
            if (launch!=null) startActivity(launch);
        });
        status=new TextView(this);layout.addView(status);
        button("刷新运行状态",this::refresh);setContentView(scroll);
    }
    private void refresh() {status.setText("最近状态："+prefs.getString("status","尚未运行")
        +"\n精确闹钟："+(DailySchedule.permitted(this)?"已允许":"待授权")
        +"\n下次运行："+(prefs.getBoolean("scheduled",false)&&DailySchedule.permitted(this)
            ?java.time.Instant.ofEpochMilli(prefs.getLong("next",0)).atZone(java.time.ZoneId.of("Asia/Shanghai")).toString():"未启用"));}
    @Override public void onResume() {super.onResume();DailySchedule.arm(this);refresh();}
}
