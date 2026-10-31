package com.zfj.dldlextension;

/** Require a new GL observation after request/focus changes; keep timing a frozen GL thread. */
final class SplashVisibility {
    private String request="";
    private boolean foreground;
    private long since=-1;
    private long resetAt;

    long update(String id,boolean focused,String observedId,boolean visible,long observedAt,long now) {
        if (!request.equals(id) || foreground!=focused) {
            request=id;foreground=focused;since=-1;resetAt=now;
        }
        if (id.isEmpty() || !focused || !id.equals(observedId) || !visible || observedAt>now) {
            since=-1;return since;
        }
        if (since<0 && observedAt>=resetAt) since=now;
        return since;
    }
}
