<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=false; section>
  <#if section = "header">
    Sign in with your operator credentials to access the console
  <#elseif section = "form">
    <#if realm.password>
    <form id="kc-form-login" action="${url.loginAction}" method="post" onsubmit="document.getElementById('kc-login').disabled = true; return true;">
      <#if !usernameHidden??>
      <div class="field">
        <label for="username"><#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>Username / Email<#else>${msg("email")}</#if></label>
        <input id="username" name="username" type="text" value="${(login.username!'')}" autocomplete="username" placeholder="john.doe or john.doe@example.org" autofocus aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>">
      </div>
      </#if>
      <div class="field">
        <label for="password">${msg("password")}</label>
        <div class="password">
          <input id="password" name="password" type="password" autocomplete="current-password" placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;" <#if usernameHidden??>autofocus</#if> aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>">
          <button type="button" class="toggle" aria-label="Show password" aria-pressed="false" tabindex="-1" onclick="var p=document.getElementById('password');var s=p.type==='password';p.type=s?'text':'password';this.setAttribute('aria-pressed',s);"><svg class="eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg><svg class="eye-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg></button>
        </div>
      </div>
      <#if messagesPerField.existsError('username','password')>
      <div class="alert" aria-live="polite">${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}</div>
      </#if>
      <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>>
      <button class="primary" id="kc-login" name="login" type="submit">Sign in</button>
    </form>
    </#if>
  </#if>
</@layout.registrationLayout>
