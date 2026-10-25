package com.zfj.dldlextension;

import java.io.StringReader;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

/** Identifies only Huawei's native picture notice, including its normal close control. */
final class HuaweiPromotion {
    static final String COMPONENT="com.huawei.hwid/com.huawei.hms.runtimekit.stub.HMSKitStandardC2NETransparentActivity1";
    private static final String GAME="com.hnzh.dldlwhjx.huawei";
    private static final String IDS="com.huawei.hms.game:id/";
    private static final Pattern BOUNDS=Pattern.compile("\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]");
    static final class Target {
        final String focus;
        final int x,y;
        Target(String focus,int x,int y) {this.focus=focus;this.x=x;this.y=y;}
    }
    private static int[] bounds(String text) {
        Matcher m=BOUNDS.matcher(text);
        if (!m.matches()) return null;
        int[] b=new int[4];
        for(int i=0;i<4;i++) {b[i]=Integer.parseInt(m.group(i+1));if(b[i]>10000) return null;}
        return b[2]>b[0] && b[3]>b[1] ? b:null;
    }
    static Target find(String snapshot) {
        if (snapshot==null || snapshot.length()>32768) return null;
        int xml=snapshot.indexOf("<?xml");
        if (xml<0) return null;
        String header=snapshot.substring(0,xml),body=snapshot.substring(xml);
        String focus=header.split("\n",2)[0].trim();
        if (!focus.startsWith("mCurrentFocus=Window{") || !focus.contains(" u0 "+COMPONENT+"}")) return null;
        boolean gameTask=false,found=false;
        for(String line:header.split("\n")) {
            line=line.trim();
            if (line.startsWith("TASK ")) gameTask=line.matches("TASK [0-9]+:"+Pattern.quote(GAME)+" id=.* userId=0 .*");
            if (line.startsWith("ACTIVITY "+COMPONENT+" ")) {
                if (found || !gameTask) return null;
                found=true;
            }
        }
        if (!found || body.contains("<!")) return null;
        try {
            DocumentBuilderFactory factory=DocumentBuilderFactory.newInstance();
            factory.setExpandEntityReferences(false);
            NodeList nodes=factory.newDocumentBuilder().parse(new InputSource(new StringReader(body))).getElementsByTagName("node");
            if(nodes.getLength()==0) return null;
            int[] outer=bounds(((Element)nodes.item(0)).getAttribute("bounds")),close=null;
            boolean image=false,checkbox=false;
            for(int i=0;i<nodes.getLength();i++) {
                Element e=(Element)nodes.item(i);
                String id=e.getAttribute("resource-id");
                if (!id.startsWith(IDS)) continue;
                if (!"com.huawei.hwid".equals(e.getAttribute("package")) || !"true".equals(e.getAttribute("enabled"))) return null;
                if (id.equals(IDS+"notice_img")) image=true;
                if (id.equals(IDS+"block_strategy_checkbox") && "本应用今日不再展示".equals(e.getAttribute("text"))) checkbox=true;
                if (id.equals(IDS+"close_image")) {
                    if(close!=null || !"关闭".equals(e.getAttribute("content-desc")) || !"true".equals(e.getAttribute("clickable"))) return null;
                    close=bounds(e.getAttribute("bounds"));
                    if(close==null) return null;
                }
            }
            if(!image || !checkbox || close==null || outer==null || close[0]<outer[0] || close[1]<outer[1]
                || close[2]>outer[2] || close[3]>outer[3] || close[2]-close[0]>(outer[2]-outer[0])/3
                || close[3]-close[1]>(outer[3]-outer[1])/3) return null;
            return new Target(focus,(close[0]+close[2])/2,(close[1]+close[3])/2);
        } catch (Exception ignored) {return null;}
    }
}
