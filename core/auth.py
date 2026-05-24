import streamlit as st
import time
import logging
from core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Session verification interval (seconds)
# Long interval to avoid drops during heavy AI operations
_AUTH_CHECK_INTERVAL = 900  # 15 minutes

# Max consecutive API failures before hard logout
_MAX_AUTH_FAILURES = 5


def login_user(email, password):
    """
    Logs in the user via Supabase Auth.
    Returns the session or None if failed.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            # Store last verified time and reset failure count
            st.session_state["_auth_last_verified"] = time.time()
            st.session_state["_auth_fail_count"] = 0
            return response
    except Exception as e:
        logger.error(f"Login error: {type(e).__name__}")
        st.error("ログインに失敗しました。メールアドレスとパスワードを確認してください。")
    return None


def logout_user():
    """Sign out the user."""
    supabase = get_supabase_client()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()


def check_auth():
    """
    Middleware-like function to check if user is authenticated.
    
    Defense-in-depth strategy:
    1. If user object exists in session_state, trust it (fast path)
    2. Only verify with Supabase API every _AUTH_CHECK_INTERVAL seconds
    3. On API failure, increment failure counter instead of immediate logout
    4. Only logout after _MAX_AUTH_FAILURES consecutive failures
    5. On transient errors, keep the session alive
    """
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        return False
    
    # Initialize failure counter
    if "_auth_fail_count" not in st.session_state:
        st.session_state["_auth_fail_count"] = 0
    
    # Skip API verification if recently checked
    last_verified = st.session_state.get("_auth_last_verified", 0)
    elapsed = time.time() - last_verified
    if elapsed < _AUTH_CHECK_INTERVAL:
        # Optimistic check passed, but we MUST ensure the Supabase client has the session
        # This is critical for RLS to work correctly
        try:
            if "access_token" in st.session_state and "refresh_token" in st.session_state:
                supabase = get_supabase_client()
                # Check if client auth needs update (simple check or just set it)
                # set_session is lightweight
                supabase.auth.set_session(
                    st.session_state.access_token,
                    st.session_state.refresh_token
                )
        except Exception:
            # If session restore fails, we might need to re-verify or just let it slide
            # Worst case, RLS fails again, but user is still 'logged in' in UI
            pass
        return True
    
    # Periodic session verification with Supabase
    try:
        supabase = get_supabase_client()
        user = supabase.auth.get_user()
        if user and user.user:
            # Success - reset failure count and update timestamp
            st.session_state["_auth_last_verified"] = time.time()
            st.session_state["_auth_fail_count"] = 0
            return True
        
        # get_user returned None/empty - try to refresh token
        try:
            refresh_resp = supabase.auth.refresh_session()
            if refresh_resp and refresh_resp.user:
                st.session_state["_auth_last_verified"] = time.time()
                st.session_state["_auth_fail_count"] = 0
                logger.info("Auth session refreshed successfully")
                return True
        except Exception as refresh_err:
            logger.warning(f"Token refresh failed: {type(refresh_err).__name__}")
        
        # Both get_user and refresh failed
        fail_count = st.session_state.get("_auth_fail_count", 0) + 1
        st.session_state["_auth_fail_count"] = fail_count
        
        if fail_count >= _MAX_AUTH_FAILURES:
            # Too many consecutive failures - session truly expired
            logger.warning(f"Auth session expired after {fail_count} consecutive failures")
            st.session_state.user = None
            return False
        
        # Not enough failures yet - keep session alive, retry next interval
        logger.warning(f"Auth check failed ({fail_count}/{_MAX_AUTH_FAILURES}), keeping session alive")
        # Push next check forward by half interval (backoff)
        st.session_state["_auth_last_verified"] = time.time() - (_AUTH_CHECK_INTERVAL / 2)
        return True
        
    except Exception as e:
        # Network/transient error - do NOT log user out
        # Keep the session alive and push next check forward
        logger.warning(f"Auth check transient error (keeping session): {type(e).__name__}: {e}")
        st.session_state["_auth_last_verified"] = time.time()
        return True
