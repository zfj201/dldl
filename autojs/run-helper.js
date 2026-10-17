/* AutoJs6 6.7：Root 开屏/截图/点击，只处理已识别登录页面；业务交给模块的完整队列。 */
var BASE = files.join(String(context.getFilesDir().getAbsolutePath()), "dldl");
var GAME = "com.hnzh.dldlwhjx.huawei";
var CHANNEL = "/data/user/0/" + GAME + "/files/dldl_extension/automation/";
var cfg = JSON.parse(files.read(files.join(BASE, "config.json")));
var lock = new java.io.File(files.join(BASE, "running.lock"));
if (lock.exists() && Date.now()-Number(lock.lastModified()) > 40*60*1000) lock.delete();
if (!lock.createNewFile()) { log("已有自动化运行或上轮锁文件未清理，停止重复启动"); exit(); }
var logPath = files.join(BASE, "last-run.log");
var templates = [];
var cityTemplate;
var wakeLock;
var launchOnly = engines.myEngine().execArgv.launchOnly === true;
function note(s) { files.append(logPath, new Date().toISOString() + " " + s + "\n"); log(s); }
function trace(s) { if (cfg.debug) files.append(logPath, new Date().toISOString() + " trace " + s + "\n"); }
function quote(s) { return "'" + String(s).replace(/'/g, "'\\''") + "'"; }
function root(cmd, allowExistingActivity) {
    // AutoJs shell() 先 waitFor 再读管道；输出较多时会互相等待。
    // 直接写私有文件并限制每条命令时间，登录循环的超时才真正有效。
    var outputPath=files.join(BASE,"root-output.txt");
    // Android 每个 App 有私有挂载命名空间；普通 su 仍看不到其他游戏的数据目录。
    // KernelSU 的 -M 切到全局挂载命名空间，Root 权限不变。
    var process=new java.lang.ProcessBuilder(java.util.Arrays.asList("su","-M","-c",cmd))
        .redirectErrorStream(true).redirectOutput(new java.io.File(outputPath)).start();
    if (!process.waitFor(20,java.util.concurrent.TimeUnit.SECONDS)) {
        process.destroyForcibly();throw Error("Root 命令超过20秒，停止本轮");
    }
    var output=files.read(outputPath), code=Number(process.exitValue());
    var existing=allowExistingActivity && /Warning: Activity not started, its current task has been brought to the front/.test(output);
    if (code !== 0 && !existing) throw Error("Root 命令失败: " + output);
    return String(output);
}
function readChannel(name) { return root("cat " + quote(CHANNEL + name) + " 2>/dev/null || true").trim().split("\t"); }
function screenshot() {
    var path = files.join(BASE, "screen.png");
    root("screencap -p " + quote(path) + " && chown " + android.os.Process.myUid() + " " + quote(path));
    return images.read(path);
}
function find(screen, template, options) {
    try { return images.findImage(screen, template, options); }
    catch (e) { trace("template-skip: "+e); return null; }
}
function gameInForeground() {
    var state = root("dumpsys activity activities | sed -n '/topResumedActivity=/p; /mResumedActivity:/p'");
    // 优先采用 topResumedActivity，避免多窗口或切换期间的旧 resumed 记录误判。
    var top = state.split("\n").filter(function(line) { return line.indexOf("topResumedActivity=") >= 0; });
    var current = top.length ? top.join("\n") : state;
    return new RegExp("\\s" + GAME.replace(/\./g, "\\.") + "/").test(current);
}
function act(screen, originalWidth, originalHeight) {
    for (var i = 0; i < templates.length; i++) {
        var t = templates[i], p = find(screen, t.image, { threshold: 0.92, level:0, region: t.region });
        if (p) {
            var x = Math.round((p.x + t.width / 2) * originalWidth / 1080);
            var y = Math.round((p.y + t.height / 2) * originalHeight / 2460);
            // 点位由当前画面的模板匹配得出，不按固定等待时间盲点。
            if (!gameInForeground()) throw Error("点击前游戏已离开前台，停止本轮");
            root("input tap " + x + " " + y); note("识别并点击: " + t.name); return true;
        }
    }
    return false;
}
function result(id) { var r = readChannel("result.tsv"); return r[0] === "v1" && r[1] === id ? r : null; }
function requireForegroundService() {
    var services = context.getSystemService(android.content.Context.ACTIVITY_SERVICE).getRunningServices(100);
    for (var i = 0; i < services.size(); i++) {
        var service = services.get(i);
        if (service.foreground && String(service.service.getPackageName()) === String(context.getPackageName())) return;
    }
    throw Error("AutoJs前台服务未开启，请打开侧栏的“前台服务”，否则切到游戏后脚本可能被系统冻结");
}
function run() {
try {
    note("开始；目标每日时间 07:00 Asia/Shanghai");
    requireForegroundService();
    // keepScreenOn 不能代替 CPU 唤醒锁；息屏定时启动时先阻止进程再次休眠。
    wakeLock = context.getSystemService(android.content.Context.POWER_SERVICE)
        .newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "dldl:daily-helper");
    wakeLock.acquire(40 * 60 * 1000);
    if (root("id").indexOf("uid=0") < 0) throw Error("没有 Root 授权");
    note("Root已确认，准备保持亮屏");
    device.keepScreenOn(40 * 60 * 1000);
    note("准备唤醒并解锁");
    root("input keyevent KEYCODE_WAKEUP; wm dismiss-keyguard");
    sleep(800);
    if (context.getSystemService(android.content.Context.KEYGUARD_SERVICE).isKeyguardLocked()) {
        root("input swipe 540 2100 540 600 450"); sleep(800);
    }
    if (context.getSystemService(android.content.Context.KEYGUARD_SERVICE).isKeyguardLocked()) throw Error("锁屏未解锁");
    note("已解锁，准备页面模板");
    cfg.templates.forEach(function(t) {
        var image = images.read(files.join(BASE, "templates", t.file));
        if (!image) throw Error("缺少页面模板 " + t.file);
        templates.push({name:t.name,image:image,width:image.width,height:image.height,region:t.region});
    });
    var citySource=images.read(files.join(BASE,"templates",cfg.readyTemplate));
    if (!citySource) throw Error("缺少主城就绪模板");
    try {cityTemplate=images.grayscale(citySource);} finally {citySource.recycle();}
    note("模板已加载，启动游戏");
    root("am start -n " + GAME + "/com.game.sdk.GameSdkActivity",true);
    note("已请求启动游戏，等待进入前台（最多45秒）");
    var until = Date.now() + 300000, ready, stable = 0;
    var foregroundUntil = Date.now() + 45000, enteredForeground = false;
    while (Date.now() < until) {
        trace("foreground");
        if (!gameInForeground()) {
            if (enteredForeground) throw Error("游戏已离开前台，停止点击");
            if (Date.now() >= foregroundUntil) throw Error("启动后45秒仍未进入游戏前台，未发送执行指令");
            sleep(1000);
            continue;
        }
        if (!enteredForeground) { enteredForeground = true; note("游戏已进入前台，开始识别页面"); }
        trace("screenshot");
        var raw = screenshot(), screen;
        try {
            trace("resize");
            screen = images.resize(raw, [1080, 2460]);
            trace("match actions");
            var clicked = act(screen,raw.width,raw.height);
            trace("read ready");
            var r = readChannel("ready.tsv");
            var fresh = r[0] === "v1" && r[1] === "ready" && Math.abs(Date.now()/1000-Number(r[5])) < 10;
            trace("match city");
            // 游戏闲置会压暗画面；灰度相关匹配保留字形判断，不依赖亮度。
            // 小字模板直接在原尺寸匹配，金字塔降采样会丢掉最高相似度位置。
            var gray=images.grayscale(screen),inCity;
            try {inCity=!!find(gray,cityTemplate,{threshold:0.95,level:0,region:[0,2220,200,230]});}
            finally {gray.recycle();}
            trace("ready="+fresh+" city="+inCity+" clicked="+clicked+" stable="+stable);
            // 清完识别到的弹窗后，连续确认客户端业务已就绪。
            if (!clicked && fresh && inCity) { stable++; if (stable >= 3) { ready=r;break; } }
            else stable=0;
        } finally { if (screen) screen.recycle(); raw.recycle(); }
        trace("sleep"); sleep(2000);
    }
    if (!ready) throw Error("进入游戏超时；保存当前截图，未发送执行指令");
    if (String(cfg.role.rid)!==ready[2] || String(cfg.role.srv_id)!==ready[3]) throw Error("当前角色与绑定角色不同");
    if (launchOnly) { note("启动验证通过：弹窗已处理、角色匹配、主城与业务连续就绪；未发送执行指令"); return; }
    var now = Math.floor(Date.now()/1000), id = "daily-" + ready[4] + "-" + ready[2];
    var text = ["v1",id,ready[2],ready[3],ready[4],now,now+240,"run_all"].join("\t") + "\n";
    var tmp = CHANNEL + "request.tsv.tmp";
    // 游戏私有目录中的指令只包含固定协议字段；先设置为游戏 UID 再原子替换。
    root("printf %s " + quote(text) + " > " + quote(tmp) + " && chmod 600 " + quote(tmp)
        + " && chown $(stat -c %u " + quote(CHANNEL) + ") " + quote(tmp)
        + " && mv " + quote(tmp) + " " + quote(CHANNEL + "request.tsv"));
    note("已发送完整队列指令 " + id);
    var end = Date.now() + 31*60*1000, last="", completed=false;
    while (Date.now() < end) {
        var status = result(id);
        if (status) {
            var summary=status.slice(2,6).join(" ");
            if (summary!==last) {note(summary);last=summary;}
            if (status[2]==="completed" || status[2]==="already_completed") {completed=true;break;}
            if (["uncertain","failed","rejected"].indexOf(status[2])>=0) throw Error("模块返回 " + summary);
        }
        sleep(2000);
    }
    if (!completed) throw Error("等待回执超时，不重发、不重启游戏");
    files.write(files.join(BASE,"last-tasks.tsv"),root("cat " + quote(CHANNEL+"tasks.tsv") + " 2>/dev/null || true"));
    screenshot().recycle();
    note("整份队列结束；各项完成/跳过状态见 last-tasks.tsv");
    if (cfg.closeGameOnComplete) root("am force-stop " + GAME);
} catch (e) {
    note("停止: " + e);
    try { screenshot().recycle(); } catch (_) {}
} finally {
    templates.forEach(function(t){t.image.recycle();});
    if (cityTemplate) cityTemplate.recycle();
    try { device.cancelKeepingAwake(); }
    finally {
        try { if (wakeLock && wakeLock.isHeld()) wakeLock.release(); }
        finally { lock.delete(); }
    }
}
}
run();
