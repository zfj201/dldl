// Run the actual AutoJs entry point with a simulated Android clock, shell and UI.
// node --test tests/test_autojs_startup.js
const assert = require('node:assert/strict');
const test = require('node:test');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../autojs/run-helper.js'), 'utf8');
const GAME = 'com.hnzh.dldlwhjx.huawei';
const game = `topResumedActivity=ActivityRecord{123 u0 ${GAME}/.Main t1}`;
const launcher = 'topResumedActivity=ActivityRecord{456 u0 com.android.launcher/.Main t2}';

function simulate(options = {}) {
    let now = 1800000000000, output = '', held = false, foregroundReads = 0, tapped = false;
    const start = now, commands = [], notes = [], events = [];
    const cfg = {
        role: {rid: '123', srv_id: '5'}, closeGameOnComplete: true,
        templates: [{name: 'APK更新以后再说', file: 'update-later.png', region: [460,1850,360,300]}],
        readyTemplate: 'city-ready.png'
    };
    function shell(cmd) {
        commands.push(cmd);
        if (cmd === 'id') {
            assert.ok(held, 'CPU lock must precede first root command');
            return options.noRoot ? 'uid=2000' : 'uid=0';
        }
        if (cmd.startsWith('dumpsys')) {
            foregroundReads++;
            if (options.foreground) return options.foreground(foregroundReads, now - start);
            return now - start < 5000 ? launcher : game;
        }
        if (cmd.startsWith('input tap')) { tapped = true; return ''; }
        if (cmd.includes('ready.tsv')) return `v1\tready\t${options.wrongRole ? '999' : '123'}\t5\t20742\t${now/1000}`;
        if (cmd.includes('result.tsv')) return 'v1\tdaily-20742-123\tcompleted\tqueue_finished\t1\t1';
        return '';
    }
    function File(name) {
        this.exists = () => false;
        this.createNewFile = () => true;
        this.delete = () => events.push('delete-lock');
    }
    function ProcessBuilder(args) {
        this.redirectErrorStream = this.redirectOutput = () => this;
        this.start = () => {
            output = shell(args[3]);
            return {waitFor: () => true, exitValue: () => 0};
        };
    }
    function img(name) {
        return {name, width: 1080, height: 2460, recycle() {}};
    }
    class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return now; } }
    vm.runInNewContext(source, {
        Date: Clock,
        context: {
            getFilesDir: () => ({getAbsolutePath: () => '/autojs'}),
            getPackageName: () => 'org.autojs.autojs6',
            getSystemService: name => name === 'power' ? {
                newWakeLock: () => ({acquire: () => {held = true; events.push('acquire');},
                    isHeld: () => held, release: () => {held = false; events.push('release');}})
            } : name === 'activity' ? {getRunningServices: () => ({size: () => options.noService ? 0 : 1,
                get: () => ({foreground: true, service: {getPackageName: () => 'org.autojs.autojs6'}})})}
                : {isKeyguardLocked: () => false}
        },
        android: {content: {Context: {POWER_SERVICE: 'power', KEYGUARD_SERVICE: 'keyguard', ACTIVITY_SERVICE: 'activity'}},
            os: {PowerManager: {PARTIAL_WAKE_LOCK: 1}, Process: {myUid: () => 12345}}},
        java: {io: {File}, lang: {ProcessBuilder}, util: {
            Arrays: {asList: (...args) => args}, concurrent: {TimeUnit: {SECONDS: 1}}
        }},
        files: {join: path.join, read: name => name.endsWith('config.json') ? JSON.stringify(cfg) : output,
            append() {}, write() {}},
        images: {read: img, resize: image => image, grayscale: image => image,
            findImage: (_, template) => template.name.includes('city-ready') ? (tapped ? {x: 1, y: 1} : null)
                : (tapped ? null : {x: 566, y: 1980})},
        device: {keepScreenOn() {}, cancelKeepingAwake() {events.push('cancel-screen');}},
        engines: {myEngine: () => ({execArgv: {launchOnly: options.launchOnly !== false}})},
        sleep: ms => {now += ms;}, log: s => notes.push(s), exit: () => {throw Error('exit');}
    }, {timeout: 2000});
    assert.equal(held, false, 'CPU wake lock must be released');
    assert.equal(events.at(-1), 'delete-lock');
    return {commands, notes, elapsed: now - start, foregroundReads};
}

test('cold launch waits for foreground, dismisses update, verifies readiness without running tasks', () => {
    const r = simulate();
    assert.ok(r.foregroundReads > 4);
    assert.equal(r.commands.filter(c => c.startsWith('input tap')).length, 1);
    assert.ok(r.notes.some(s => s.includes('启动验证通过')));
    assert.ok(!r.commands.some(c => c.includes('request.tsv') || c.startsWith('am force-stop')));
});
test('game never enters foreground: bounded timeout and no clicks or requests', () => {
    const r = simulate({foreground: () => launcher});
    assert.ok(r.elapsed >= 45000 && r.elapsed < 48000);
    assert.ok(r.notes.some(s => s.includes('45秒仍未进入')));
    assert.ok(!r.commands.some(c => c.startsWith('input tap') || c.includes('request.tsv')));
});
test('foreground changes after screenshot: do not click another app', () => {
    const r = simulate({foreground: n => n === 1 ? game : launcher});
    assert.ok(r.notes.some(s => s.includes('点击前游戏已离开')));
    assert.ok(!r.commands.some(c => c.startsWith('input tap') || c.includes('request.tsv')));
});
test('top resumed app wins over a stale game mResumedActivity record', () => {
    const r = simulate({foreground: () => launcher + '\n' + game.replace('topResumedActivity=', 'mResumedActivity: ')});
    assert.ok(r.notes.some(s => s.includes('45秒仍未进入')));
    assert.ok(!r.commands.some(c => c.startsWith('input tap')));
});
test('normal scheduled mode still sends exactly one request and completes', () => {
    const r = simulate({launchOnly: false});
    assert.equal(r.commands.filter(c => c.startsWith('printf %s') && c.includes('request.tsv')).length, 1);
    assert.ok(r.commands.some(c => c === `am force-stop ${GAME}`));
});
test('role mismatch never sends a queue request', () => {
    const r = simulate({launchOnly: false, wrongRole: true});
    assert.ok(r.notes.some(s => s.includes('角色与绑定角色不同')));
    assert.ok(!r.commands.some(c => c.includes('request.tsv')));
});
test('early root failure releases wake lock and run lock', () => {
    const r = simulate({noRoot: true});
    assert.ok(r.notes.some(s => s.includes('没有 Root 授权')));
});
test('missing foreground service stops before launching game with an actionable message', () => {
    const r = simulate({noService: true});
    assert.ok(r.notes.some(s => s.includes('AutoJs前台服务未开启')));
    assert.ok(!r.commands.some(c => c.startsWith('am start') || c.includes('request.tsv')));
});
