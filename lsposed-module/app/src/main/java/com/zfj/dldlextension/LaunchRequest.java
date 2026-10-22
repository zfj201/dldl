package com.zfj.dldlextension;

/** Private-file protocol shared by the scheduler and the injected SDK hooks. */
final class LaunchRequest {
    final String id, rid, server, mode;
    final long created, expires;
    private LaunchRequest(String[] p) {
        id=p[1]; rid=p[2]; server=p[3]; created=Long.parseLong(p[4]); expires=Long.parseLong(p[5]); mode=p[6];
    }
    static LaunchRequest parse(String text, long now) {
        if (text.length()>512) return null;
        String[] p=text.replaceFirst("\n$", "").split("\t", -1);
        if (p.length!=7 || !p[0].equals("v1") || !p[1].matches("[A-Za-z0-9_-]{1,80}")
                || !p[2].matches("[A-Za-z0-9_-]+") || !p[3].matches("[A-Za-z0-9_-]+")
                || !(p[6].equals("run_all") || p[6].equals("verify"))) return null;
        try {
            LaunchRequest r=new LaunchRequest(p);
            return r.created>=0 && r.expires>=r.created && r.expires-r.created<=300
                    && now>=r.created-5 && now<=r.expires ? r : null;
        } catch (NumberFormatException e) { return null; }
    }
}
