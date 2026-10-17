/* 只验证启动、弹窗和角色就绪，不发送助手执行指令。 */
var base = files.join(String(context.getFilesDir().getAbsolutePath()), "dldl");
engines.execScriptFile(files.join(base, "run-helper.js"), {
    arguments: {launchOnly: true}
});
