<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="${(locale.currentLanguageTag)!'en'}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>${(realm.displayName)!realm.name} &middot; Eunomia DS-Agent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@500;600&amp;family=Source+Sans+3:wght@400;500;600&amp;family=Source+Code+Pro:wght@400;600&amp;display=swap" rel="stylesheet">
    <link href="${url.resourcesPath}/css/eunomia.css" rel="stylesheet">
  </head>
  <body class="${bodyClass}">
    <aside class="brand">
      <div class="bubbles" aria-hidden="true">
        <div class="bubble b1"></div>
        <div class="orbit o2"><div class="bubble"></div></div>
        <div class="orbit o3"><div class="bubble"></div></div>
        <div class="bubble b4"></div>
        <div class="orbit o5"><div class="bubble"></div></div>
        <div class="bubble b6"></div>
      </div>
      <div class="glass">
        <img class="logo" src="${url.resourcesPath}/img/eunomia-logo.svg" alt="Eunomia">
        <div>
          <p class="tagline">Trusted data spaces for a sovereign digital economy.</p>
          <p class="protocols">Dataspace Protocol &bull; Identity &amp; Authority &bull; Access Control</p>
        </div>
        <div class="status"><span class="dot"></span><span>${(realm.displayName)!realm.name} connector</span></div>
      </div>
    </aside>
    <main class="panel">
      <div class="content">
        <div class="heading">
          <div class="eyebrow"><span class="dot"></span>OAuth 2.0 / OIDC Authentication</div>
          <h1>Eunomia DS-Agent Admin</h1>
          <#if auth?has_content && auth.showUsername() && !auth.showResetCredentials()>
          <p class="subtitle">${auth.attemptedUsername} &middot; <a href="${url.loginRestartFlowUrl}">${msg("restartLoginTooltip")}</a></p>
          <#else>
          <p class="subtitle"><#nested "header"></p>
          </#if>
          <span class="connector">${(realm.displayName)!realm.name}</span>
        </div>
        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
        <div class="alert alert-${message.type}">${kcSanitize(message.summary)?no_esc}</div>
        </#if>
        <#nested "form">
        <#nested "socialProviders">
        <#if displayInfo>
        <div class="info"><#nested "info"></div>
        </#if>
        <p class="footnote">Secured with OpenID Connect &middot; Keycloak</p>
      </div>
    </main>
    <script>
      (function () {
        var brand = document.querySelector(".brand");
        var glow = document.querySelector(".b6");
        if (!brand || !glow) return;
        brand.addEventListener("mousemove", function (e) {
          var r = brand.getBoundingClientRect();
          var x = e.clientX - r.left - r.width / 2;
          var y = e.clientY - r.top - r.height / 2;
          glow.style.transform = "translate(" + x + "px, " + y + "px)";
        });
      })();
    </script>
  </body>
</html>
</#macro>
