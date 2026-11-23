// Cria o usuario admin do Jenkins com a senha do .env e exige login para tudo
import jenkins.model.Jenkins
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy

def jenkins = Jenkins.get()
def senha = System.getenv("JENKINS_ADMIN_SENHA") ?: "troque-esta-senha"
def realm = jenkins.getSecurityRealm()
if (!(realm instanceof HudsonPrivateSecurityRealm)) {
    realm = new HudsonPrivateSecurityRealm(false)
    jenkins.setSecurityRealm(realm)
}
if (hudson.model.User.getById("admin", false) == null) {
    realm.createAccount("admin", senha)
}
def estrategia = new FullControlOnceLoggedInAuthorizationStrategy()
estrategia.setAllowAnonymousRead(false)
jenkins.setAuthorizationStrategy(estrategia)
jenkins.save()
