#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
mkdir -p "$TASK_TMP/com/zfj/dldlextension"
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/HuaweiPromotion.java" "$TASK_TMP/com/zfj/dldlextension/"
cat > "$TASK_TMP/com/zfj/dldlextension/HuaweiPromotionTest.java" <<'JAVA'
package com.zfj.dldlextension;
import java.nio.file.Files;
import java.nio.file.Path;
public class HuaweiPromotionTest {
    static String header="mCurrentFocus=Window{123 u0 "+HuaweiPromotion.COMPONENT+"}\n"
        +"TASK 10303:com.hnzh.dldlwhjx.huawei id=1 userId=0 displayId=0(type=INTERNAL)\n"
        +"  ACTIVITY "+HuaweiPromotion.COMPONENT+" abc pid=123 userId=0\n";
    static void reject(String s) {if(HuaweiPromotion.find(s)!=null) throw new AssertionError("unsafe promotion match");}
    public static void main(String[] args) throws Exception {
        String xml=Files.readString(Path.of(args[0]));
        HuaweiPromotion.Target t=HuaweiPromotion.find(header+xml);
        if(t==null || t.x!=948 || t.y!=716) throw new AssertionError("real native notice not identified");
        t=HuaweiPromotion.find(header+xml.replace("[882,650][1014,782]","[720,330][840,450]"));
        if(t==null || t.x!=780 || t.y!=390) throw new AssertionError("close follows control bounds");
        reject(header.replace("TASK 10303:com.hnzh.dldlwhjx.huawei","TASK 10303:other.game")+xml);
        reject(header.replace("TASK 10303:com.hnzh.dldlwhjx.huawei","TASK 10303:com.hnzh.dldlwhjx.huawei.evil")+xml);
        reject(header.replace("userId=0","userId=10")+xml);
        reject(header.replace(" u0 "," u10 ")+xml);
        reject(header.replace(HuaweiPromotion.COMPONENT,"com.huawei.hwid/.LoginActivity")+xml);
        reject(header.replace("  ACTIVITY ","  UNKNOWN ")+xml);
        reject(header+xml.replace("package=\"com.huawei.hwid\"","package=\"other.app\""));
        reject(header+xml.replace("id/notice_img","id/login_prompt"));
        reject(header+xml.replace("本应用今日不再展示","允许登录"));
        reject(header+xml.replace("content-desc=\"关闭\"","content-desc=\"支付\""));
        reject(header+xml.replace("enabled=\"true\"","enabled=\"false\""));
        reject(header+xml.replace("clickable=\"true\"","clickable=\"false\""));
        reject(header+xml.replace("[882,650][1014,782]","[882,650][882,782]"));
        reject(header+xml.replace("[882,650][1014,782]","[0,0][132,132]"));
        reject(header+xml.replace("[882,650][1014,782]","[0,0][1080,2460]"));
        reject(header+xml.replace("id/notice_setting","id/close_image"));
        reject(header+xml.replace("<hierarchy", "<!DOCTYPE x><hierarchy"));
        reject(header+xml+"x".repeat(32768));
        reject(header);reject(null);
        System.out.println("Huawei promotion: real fixture, dynamic bounds, task/window/package isolation, login/payment negatives and malformed controls passed");
    }
}
JAVA
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/javac" -d "$TASK_TMP" \
    "$TASK_TMP/com/zfj/dldlextension/HuaweiPromotion.java" "$TASK_TMP/com/zfj/dldlextension/HuaweiPromotionTest.java"
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/java" -cp "$TASK_TMP" \
    com.zfj.dldlextension.HuaweiPromotionTest "$ROOT/tests/fixtures/huawei_promotion.xml"
