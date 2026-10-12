VERSION="4.13.2"

curl -o "./antlr4/antlr-$VERSION-complete.jar" "https://www.antlr.org/download/antlr-$VERSION-complete.jar"

export CLASSPATH="$PWD/antlr/antlr-$VERSION-complete.jar:$CLASSPATH"
# simplify the use of the tool to generate lexer and parser
alias antlr4="java -Xmx500M -cp '$PWD/antlr4/antlr-$VERSION-complete.jar:$CLASSPATH' org.antlr.v4.Tool"
# simplify the use of the tool to test the generated code
alias grun="java -Xmx500M -cp '$PWD/antlr4/antlr-$VERSION-complete.jar:$CLASSPATH' org.antlr.v4.gui.TestRig"

uv pip install antlr4-python3-runtime

cat << EOF

Done!

You can now run

antlr4 -Dlanguage=Python3 -visitor Hql.g4
EOF
