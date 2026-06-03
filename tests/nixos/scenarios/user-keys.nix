{ pkgs, agenix, agenixManagerModule, common }:
let
  user1Key = common.genKeyPair "user1";
  user2Key = common.genKeyPair "user2";
  user1PubText = builtins.readFile "${user1Key}/key.pub";
  user2PubText = builtins.readFile "${user2Key}/key.pub";

  secret1 = common.encrypt "user-secret-1" [ user1Key ] "user-1-data";
  secret2 = common.encrypt "user-secret-2" [ user2Key ] "user-2-data";
  secret3 = common.encrypt "shared-secret" [ user1Key user2Key ] "both-users";
in {
  name = "user-keys";

  nodeConfig = { config, pkgs, ... }: {
    imports = [ agenix.nixosModules.default agenixManagerModule ];

    system.activationScripts.activatePlaceAgenixTestFiles = {
      text = ''
        mkdir -p /etc/secrets /etc/agenix
        cp ${user1Key}/key /etc/agenix/user1_key
        chmod 0600 /etc/agenix/user1_key
        cp ${user2Key}/key /etc/agenix/user2_key
        chmod 0600 /etc/agenix/user2_key
        cp ${secret1} /etc/secrets/user-secret-1.age
        chmod 0644 /etc/secrets/user-secret-1.age
        cp ${secret2} /etc/secrets/user-secret-2.age
        chmod 0644 /etc/secrets/user-secret-2.age
        cp ${secret3} /etc/secrets/shared-secret.age
        chmod 0644 /etc/secrets/shared-secret.age
      '';
      deps = [];
    };

    agenixManager = {
      enable = true;
      secretsPath = "/etc/secrets";
      flakeRoot = "/etc/nixos";
      keys.users = [ user1PubText user2PubText ];
      identities = [
        "/etc/agenix/user1_key"
        "/etc/agenix/user2_key"
      ];
      secrets = [
        { name = "user-secret-1"; keys = "users"; }
        { name = "user-secret-2"; keys = "users"; }
        { name = "shared-secret";  keys = "users"; }
      ];
    };

    system.stateVersion = config.system.nixos.release;
  };

  testScript = ''
    machine.wait_for_unit("multi-user.target")

    content = machine.succeed("cat /etc/agenix/secrets.nix")
    assert "user-secret-1.age" in content
    assert "user-secret-2.age" in content
    assert "shared-secret.age" in content

    s1 = machine.succeed("cat /run/agenix/user-secret-1").strip()
    assert s1 == "user-1-data", f"user-secret-1 mismatch: {s1}"

    s2 = machine.succeed("cat /run/agenix/user-secret-2").strip()
    assert s2 == "user-2-data", f"user-secret-2 mismatch: {s2}"

    s3 = machine.succeed("cat /run/agenix/shared-secret").strip()
    assert s3 == "both-users", f"shared-secret mismatch: {s3}"
  '';
}
