package middleware

import (
	"context"
	"eunomia-demo-factory/internal/config"
	"strings"

	"github.com/coreos/go-oidc/v3/oidc"
	"github.com/gin-gonic/gin"
)

func AuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	var provider *oidc.Provider
	var verifier *oidc.IDTokenVerifier

	return func(c *gin.Context) {
		// Lazy initialize provider
		if provider == nil {
			var err error
			issuerURL := cfg.KeycloakURL + "/realms/" + cfg.KeycloakRealm

			// FIX: Since we use Kubernetes service names internally (the keycloak service)
			// but Keycloak reports itself as the external domain (nip.io),
			// we use an "Insecure" context to allow the library to fetch metadata
			// from the service URL even if the issuer name inside doesn't match.
			ctx := oidc.InsecureIssuerURLContext(context.Background(), issuerURL)

			provider, err = oidc.NewProvider(ctx, issuerURL)
			if err != nil {
				println("OIDC Provider Error:", err.Error())
				c.AbortWithStatusJSON(500, gin.H{"error": "Authentication provider unavailable"})
				return
			}
			// Skip issuer check because internal name != external name
			// Skip client ID check (audience) because Keycloak tokens often don't include it by default
			verifier = provider.Verifier(&oidc.Config{
				ClientID:          cfg.KeycloakClientID,
				SkipIssuerCheck:   true,
				SkipClientIDCheck: true,
			})
		}

		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.AbortWithStatusJSON(401, gin.H{"error": "Authorization header required"})
			return
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.AbortWithStatusJSON(401, gin.H{"error": "Invalid authorization header format"})
			return
		}

		tokenString := parts[1]
		idToken, err := verifier.Verify(context.Background(), tokenString)
		if err != nil {
			c.AbortWithStatusJSON(401, gin.H{"error": "Invalid token: " + err.Error()})
			return
		}

		// Extract claims if needed
		var claims map[string]interface{}
		if err := idToken.Claims(&claims); err != nil {
			c.AbortWithStatusJSON(500, gin.H{"error": "Failed to parse claims"})
			return
		}

		c.Set("claims", claims)
		c.Set("user_id", idToken.Subject)

		c.Next()
	}
}
