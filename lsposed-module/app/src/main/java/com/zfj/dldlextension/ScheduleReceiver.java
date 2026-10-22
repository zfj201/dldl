package com.zfj.dldlextension;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class ScheduleReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent) {
        DailySchedule.arm(context); // re-arm first; a failed run must not remove tomorrow's alarm.
        if ("com.zfj.dldlextension.VERIFY".equals(intent.getAction())) {
            context.startForegroundService(new Intent(context,AutomationService.class).setAction("verify"));
        }
        if ("com.zfj.dldlextension.DAILY".equals(intent.getAction())
                && DailySchedule.prefs(context).getBoolean("scheduled",false)) {
            context.startForegroundService(new Intent(context,AutomationService.class).setAction("run_all"));
        }
    }
}
