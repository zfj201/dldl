#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
mkdir -p "$TASK_TMP/com/zfj/dldlextension"
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/LoadingRecovery.java" "$TASK_TMP/com/zfj/dldlextension/"
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/SplashVisibility.java" "$TASK_TMP/com/zfj/dldlextension/"
cat > "$TASK_TMP/com/zfj/dldlextension/LoadingRecoveryTest.java" <<'JAVA'
package com.zfj.dldlextension;
public class LoadingRecoveryTest {
    static String sample(long since,long observed) {return "v1\trun-1\t123\t"+since+"\t"+observed+"\tvisible\n";}
    static void expect(LoadingRecovery r,String sample,String status,long now,LoadingRecovery.Decision expected) {
        if(r.inspect(sample,"run-1",status,now)!=expected) throw new AssertionError(sample+" / "+status);
    }
    public static void main(String[] args) {
        LoadingRecovery r=new LoadingRecovery();
        expect(r,sample(1000,16000),"",16000,LoadingRecovery.Decision.NONE);
        expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.RESTART);
        for(String invalid:new String[]{"",sample(1000,16001).replace("run-1","other"),
            sample(1000,16001).replace("visible","hidden"),sample(-1,16001),sample(20000,16001),
            sample(1000,16001).replace("123","0"),sample(1000,16001).replace("123","x")})
            expect(r,invalid,"",16001,LoadingRecovery.Decision.NONE);
        expect(r,sample(1000,2000),"",19002,LoadingRecovery.Decision.RESTART); // UI thread froze after showing
        expect(r,sample(1000,16001),"",16000,LoadingRecovery.Decision.NONE); // clock mismatch
        expect(r,sample(10000,17000),"",17000,LoadingRecovery.Decision.NONE); // new continuous visibility
        for(int i=0;i<3;i++) {expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.RESTART);r.restarted();}
        expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.EXHAUSTED);
        for(String phase:new String[]{"entering\tstart_adventure","waiting\twaiting_city_and_helper",
            "submitted\thelper_requested","running\texecuting","completed\tqueue_finished","blocked\trequired_update"}) {
            r=new LoadingRecovery();
            expect(r,sample(1000,16001),"v1\trun-1\t"+phase+"\t1",16001,LoadingRecovery.Decision.NONE);
            expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.NONE); // never recover after progress
        }
        r=new LoadingRecovery();
        expect(r,sample(1000,16001),"v1\told\tcompleted\tqueue_finished\t1",16001,LoadingRecovery.Decision.RESTART);
        expect(r,sample(1000,16001),"v1\trun-1\twaiting\twaiting_sdk_or_login\t1",16001,LoadingRecovery.Decision.RESTART);
        if (!LoadingRecovery.validSampleFile("startup-splash.tsv") || !LoadingRecovery.validSampleFile("sdk-loading.tsv")
                || LoadingRecovery.validSampleFile("../launch.tsv")) throw new AssertionError("sample allowlist");
        SplashVisibility splash=new SplashVisibility();
        if(splash.update("run-1",true,"run-1",true,100,200)!=-1) throw new AssertionError("stale initial GL sample");
        if(splash.update("run-1",true,"run-1",true,300,300)!=300) throw new AssertionError("start timing");
        if(splash.update("run-1",true,"run-1",true,300,16000)!=300) throw new AssertionError("frozen GL timer");
        if(splash.update("run-1",false,"run-1",true,300,17000)!=-1) throw new AssertionError("background reset");
        if(splash.update("run-1",true,"run-1",true,300,18000)!=-1) throw new AssertionError("resume needs new GL sample");
        if(splash.update("run-1",true,"run-1",true,18100,18100)!=18100) throw new AssertionError("resume timer");
        if(splash.update("run-1",true,"run-1",false,18200,18200)!=-1) throw new AssertionError("scene removed");
        if(splash.update("run-1",true,"run-1",true,18300,18300)!=18300) throw new AssertionError("scene reappeared");
        if(splash.update("run-2",true,"run-1",true,18300,18400)!=-1) throw new AssertionError("request isolation");
        if(splash.update("run-2",true,"run-2",true,18500,18500)!=18500) throw new AssertionError("new request");
        if(splash.update("",true,"run-2",true,18500,18600)!=-1) throw new AssertionError("manual launch inactive");
        // Both sources use one recovery instance and therefore one three-restart budget.
        r=new LoadingRecovery();
        for (String source:new String[]{LoadingRecovery.SDK_SAMPLE,LoadingRecovery.SPLASH_SAMPLE,LoadingRecovery.SDK_SAMPLE}) {
            expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.RESTART);r.restarted();
        }
        expect(r,sample(1000,16001),"",16001,LoadingRecovery.Decision.EXHAUSTED);
        System.out.println("Loading recovery: 15s boundary, visibility, frozen UI, identity, progress isolation and restart limit passed");
    }
}
JAVA
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/javac" -d "$TASK_TMP" "$TASK_TMP"/com/zfj/dldlextension/*.java
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/java" -cp "$TASK_TMP" com.zfj.dldlextension.LoadingRecoveryTest
