{
  lib,
  ...
}: let
  t = lib.types;
in {
  options.derivation = lib.mkOption {
    type = lib.types.record {
      fields = {
        name = lib.mkOption {
          type = t.str;
        };
        system = lib.mkOption {
          type = t.str;
        };
        builder = lib.mkOption {
          type = t.str;
        };
        args = lib.mkOption {
          type = t.listOf (t.oneOf [t.str t.path]);
        };
        buildInputs = lib.mkOption {
          type = t.listOf (t.nullOr (t.either t.package t.path));
        };
        nativeBuildInputs = lib.mkOption {
          type = t.listOf (t.nullOr (t.either t.package t.path));
        };
        propagatedBuildInputs = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        propagatedNativeBuildInputs = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsBuildBuild = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsBuildBuildPropagated = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsBuildTarget = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsBuildTargetPropagated = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsHostHost = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsHostHostPropagated = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsTargetTarget = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        depsTargetTargetPropagated = lib.mkOption {
          type = t.listOf (t.nullOr t.package);
        };
        configureFlags = lib.mkOption {
          type = t.listOf (t.either t.str (t.listOf t.str));
        };
        cmakeFlags = lib.mkOption {
          type = t.listOf t.str;
        };
        mesonFlags = lib.mkOption {
          type = t.listOf t.str;
        };
      };
      wildcard = lib.mkOption {
        type = lib.types.raw;
      };
    };
  };
  options.public = lib.mkOption {
    type = lib.types.raw;
  };
}
