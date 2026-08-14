-include Makefile.env
export

.PHONY: $(wildcard *)

ARGS := $(word 2,$(MAKECMDGOALS))

## help: show help
help:
	@echo ""
	@echo "Usage:"
	@echo ""
	@sed -n 's/^## //p' Makefile | column -t -s ':' | sed -e 's/^/\t/'
	@echo ""


%:
	@:

## update-skill: reinstall all remote skills
update-skill:
	@skillshare backup && \
	skillshare uninstall --all --force; \
	skillshare install --force mattpocock/skills && \
	skillshare install --force jakubkrehel/skills 
	skillshare install --force 0x0funky/agent-sprite-forge && \
	skillshare install --force dietrichgebert/ponytail && \
	skillshare install --force yanun0323/skills

## sync: sync skillshare to all target
sync:
	@skillshare sync extras -f; skillshare sync -f