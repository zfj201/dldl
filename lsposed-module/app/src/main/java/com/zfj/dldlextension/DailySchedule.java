package com.zfj.dldlextension;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import java.time.ZoneId;
import java.time.ZonedDateTime;

final class DailySchedule {
    static SharedPreferences prefs(Context c) {return c.getSharedPreferences("automation",Context.MODE_PRIVATE);}
    static PendingIntent pending(Context c) {
        return PendingIntent.getBroadcast(c,7,new Intent(c,ScheduleReceiver.class).setAction("com.zfj.dldlextension.DAILY"),
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    }
    static boolean permitted(Context c) {
        return android.os.Build.VERSION.SDK_INT<31 || c.getSystemService(AlarmManager.class).canScheduleExactAlarms();
    }
    static void arm(Context c) {
        AlarmManager manager=c.getSystemService(AlarmManager.class);
        manager.cancel(pending(c));
        if (!prefs(c).getBoolean("scheduled",false) || !permitted(c)) return;
        ZonedDateTime now=ZonedDateTime.now(ZoneId.of("Asia/Shanghai"));
        ZonedDateTime next=now.withHour(7).withMinute(0).withSecond(0).withNano(0);
        if (!next.isAfter(now)) next=next.plusDays(1);
        manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next.toInstant().toEpochMilli(),pending(c));
        prefs(c).edit().putLong("next",next.toInstant().toEpochMilli()).apply();
    }
    static void verifyIn30Seconds(Context c) {
        if (!permitted(c)) throw new IllegalStateException("请先允许精确闹钟");
        PendingIntent test=PendingIntent.getBroadcast(c,8,new Intent(c,ScheduleReceiver.class).setAction("com.zfj.dldlextension.VERIFY"),
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        c.getSystemService(AlarmManager.class).setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,System.currentTimeMillis()+30000,test);
    }
    private DailySchedule() {}
}
