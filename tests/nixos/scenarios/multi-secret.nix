{ pkgs, agenix, agenixManagerModule, common }:
let
  systemKey = common.genKeyPair "system";
  userKey = common.genKeyPair "user";
  systemPubText = builtins.readFile "${systemKey}/key.pub";
  userPubText = builtins.readFile "${userKey}/key.pub";

  secret1 = common.encrypt "db-password" [ systemKey ] "s3cr3t-db";
  secret2 = common.encrypt "api-token" [ userKey ] "tok-abc123";
  secret3 = common.encrypt "master-key" [ systemKey userKey ] "master-key-value";
in {
  name = "multi-secret";

  nodeConfig = { config, pkgs, ... }: {
    imports = [ agenix.nixosModules.default agenixManagerModule ];

    system.activationScripts.activatePlaceAgenixTestFiles = {
      text = ''
        mkdir -p /etc/secrets /etc/ssh /etc/agenix
        cp ${systemKey}/key /etc/ssh/ssh_host_ed25519_key
        chmod 0600 /etc/ssh/ssh_host_ed25519_key
        cp ${userKey}/key /etc/agenix/user_key
        chmod 0600 /etc/agenix/user_key
        cp ${secret1} /etc/secrets/db-password.age
        chmod 0644 /etc/secrets/db-password.age
        cp ${secret2} /etc/secrets/api-token.age
        chmod 0644 /etc/secrets/api-token.age
        cp ${secret3} /etc/secrets/master-key.age
        chmod 0644 /etc/secrets/master-key.age
      '';
      deps = [];
    };

    agenixManager = {
      enable = true;
      secretsPath = "/etc/secrets";
      flakeRoot = "/etc/nixos";
      keys = {
        systems = [ systemPubText ];
        users = [ userPubText ];
      };
      identities = [
        "/etc/ssh/ssh_host_ed25519_key"
        "/etc/agenix/user_key"
      ];
      secrets = [
        { name = "db-password";  keys = "systems"; }
        { name = "api-token";    keys = "users"; }
        { name = "master-key";   keys = "all"; }
      ];
    };

    system.stateVersion = config.system.nixos.release;
  };

  testScript = ''
    machine.wait_for_unit("multi-user.target")

    content = machine.succeed("cat /etc/agenix/secrets.nix")
    assert "db-password.age" in content, "secrets.nix missing db-password.age"
    assert "api-token.age" in content, "secrets.nix missing api-token.age"
    assert "master-key.age" in content, "secrets.nix missing master-key.age"

    db = machine.succeed("cat /run/agenix/db-password").strip()
    assert db == "s3cr3t-db", f"db-password mismatch: {db}"

    api = machine.succeed("cat /run/agenix/api-token").strip()
    assert api == "tok-abc123", f"api-token mismatch: {api}"

    master = machine.succeed("cat /run/agenix/master-key").strip()
    assert master == "master-key-value", f"master-key mismatch: {master}"
  '';
}
