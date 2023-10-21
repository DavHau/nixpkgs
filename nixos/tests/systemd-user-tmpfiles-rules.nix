import ./make-test-python.nix ({ lib, ... }: {
  name = "systemd-user-tmpfiles-rules";

  meta = with lib.maintainers; {
    maintainers = [ schnusch ];
  };

  nodes.machine = { ... }: {
    users.users = {
      alice.isNormalUser = true;
      bob.isNormalUser = true;
    };

    systemd.user.tmpfiles = {
      rules = [
        "d %h/user_tmpfiles_created"
      ];
      users.alice.rules = [
        "d %h/only_alice"
      ];
    };
    systemd.tmpfiles.files.my-service."%h/only_bob".d = {};
  };

  testScript = { ... }: ''
    machine.succeed("loginctl enable-linger alice bob")

    machine.wait_until_succeeds("systemctl --user --machine=alice@ is-active systemd-tmpfiles-setup.service")
    machine.succeed("[ -d ~alice/user_tmpfiles_created ]")
    machine.succeed("[ -d ~alice/only_alice ]")

    machine.wait_until_succeeds("systemctl --user --machine=bob@ is-active systemd-tmpfiles-setup.service")
    machine.succeed("[ -d ~bob/user_tmpfiles_created ]")
    machine.succeed("[ ! -e ~bob/only_alice ]")

    machine.succeed("stat ~bob/only_bob")
  '';
})
