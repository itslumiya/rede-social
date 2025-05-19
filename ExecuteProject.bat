@echo off
REM Verifica se o container Redis já existe
docker ps -a --filter "name=^redis$" --format "{{.Names}}" | findstr /b /c:"redis" >nul
if errorlevel 1 (
    echo [INFO] Container do Redis não encontrado. Criando um novo container...
    docker run -d -p 6379:6379 --name redis redis
    timeout /t 5 /nobreak >nul
) else (
    REM Verifica se o container Redis está parado
    docker ps --filter "name=^redis$" --format "{{.Names}}" | findstr /b /c:"redis" >nul
    if errorlevel 1 (
        echo [INFO] Container Redis existe, mas está parado. Iniciando...
        docker start redis
        timeout /t 5 /nobreak >nul
    ) else (
        echo [INFO] Container Redis já está em execução.
    )
)

REM Inicia os scripts da aplicação
start cmd /k dotnet run --project C:\Users\user\Desktop\rede-social\ProxyPubSub\ProxyPubSub.csproj
start cmd /k python C:\Users\user\Desktop\rede-social\Broker.py
start cmd /k python C:\Users\user\Desktop\rede-social\Server.py
start cmd /k node C:\Users\user\Desktop\rede-social\AutomaticFruitPublisher.js
start cmd /k python C:\Users\user\Desktop\rede-social\InteractiveUser.py
start cmd /k python C:\Users\user\Desktop\rede-social\InteractiveUser.py

echo.
echo Pressione qualquer tecla para ENCERRAR todos os serviços e limpar os dados do Redis...
pause >nul

echo [INFO] Limpando os dados do Redis...
docker exec redis redis-cli FLUSHALL

echo [INFO] Parando o container Redis...
docker stop redis >nul

echo [INFO] Removendo o container Redis...
docker rm redis >nul

echo [INFO] Finalizado com sucesso!