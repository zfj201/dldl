/* AutoJs6 新版持久定时接口是 tasks；只替换本脚本路径已有的定时，避免重复。 */
var base=files.join(String(context.getFilesDir().getAbsolutePath()),"dldl");
var script=files.join(base,"run-helper.js");
if (String(java.util.TimeZone.getDefault().getID())!=="Asia/Shanghai") throw Error("手机时区不是 Asia/Shanghai，尚未设置定时");
if (!files.exists(files.join(base,"config.json"))) throw Error("请先绑定角色和页面模板");
tasks.queryTimedTasks({path:script}).forEach(function(t){tasks.removeTimedTask(t.id);});
var task=tasks.addDailyTask({path:script,time:"07:00"});
files.write(files.join(base,"schedule.json"),JSON.stringify({id:Number(task.id),path:script,time:"07:00",timezone:"Asia/Shanghai"}));
log("已创建每天北京时间07:00完整助手队列任务，id="+task.id);
