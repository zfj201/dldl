package com.zfj.dldlextension;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.widget.Button;

public final class MainActivity extends Activity {
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(40, 60, 40, 40);
        TextView text = new TextView(this); text.setTextSize(18);
        text.setText("香香小助手扩展 " + BuildConfig.VERSION_NAME
            + "\n\n在 LSPosed 中启用本模块并勾选斗罗大陆，然后重启游戏。"
            + "\n\n扩展会自动添加 14 个日常功能入口。任务由你在游戏助手中手动执行，原有开关和次数设置会保留。"
            + "\n\n停用：在 LSPosed 中关闭本模块，然后重启游戏。"
            + "\n\n兼容性：已针对当前客户端验证，游戏接口或加载框架变化时可能需要更新模块。"
            + "\n\n旧版 game_start 组合包需要先完成迁移；模块发现旧扩展时会停止重复挂载。");
        layout.addView(text);
        Button button = new Button(this); button.setText("打开游戏");
        button.setOnClickListener(v -> {
            android.content.Intent intent = getPackageManager().getLaunchIntentForPackage("com.hnzh.dldlwhjx.huawei");
            if (intent != null) startActivity(intent);
        }); layout.addView(button);
        setContentView(layout);
    }
}
