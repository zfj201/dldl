package com.zfj.dldlextension;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public final class MainActivity extends Activity {
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        TextView text = new TextView(this);
        text.setPadding(40, 60, 40, 40);
        text.setTextSize(18);
        text.setText("斗罗扩展接入验证\n\n阶段：" + BuildConfig.PROBE_STAGE
            + "\n仅作用于斗罗大陆游戏主进程。\n在 LSPosed 中启用并勾选游戏后，重新启动游戏。"
            + "\n\n验证阶段不自动执行任何日常任务。\n停用模块并重启游戏即可撤销接入。");
        setContentView(text);
    }
}
