domain := messages
localedir := locale
langs := en ja

.PHONY: all
all:
	echo '501 Not implemented'

.PHONY: clean
clean:
	rm -f $(localedir)/$(domain).pot
	for lang in $(langs); do \
		rm -fr "$(localedir)/$${lang}"; \
	done

.PHONY: mo
mo:
	for lang in $(langs); do \
		langdir="$(localedir)/$${lang}/LC_MESSAGES"; \
		mkdir -p "$${langdir}"; \
		msgfmt --verbose --output-file "$${langdir}/$(domain).mo" "$(localedir)/$${lang}.po"; \
	done

.PHONY: po
po: pot
	for lang in $(langs); do \
		langpo="$(localedir)/$${lang}.po"; \
		if [ ! -f "$${langpo}" ]; then \
			msginit --input "$(localedir)/$(domain).pot" --no-translator --locale $${lang} --output-file "$${langpo}"; \
			echo "Please edit Header entry for $${langpo}"; \
		fi; \
		msgmerge --update --backup none --no-location --sort-output "$${langpo}" "$(localedir)/$(domain).pot"; \
	done

.PHONY: pot
pot:
	mkdir -p $(localedir)
	pygettext --default-domain $(domain) --output-dir $(localedir) --output $(domain).pot *.py

