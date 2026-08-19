# Obtener una API key de Groq

Alberdi Bot necesita una API key de Groq para generar las respuestas del chat. Groq ofrece claves gratuitas con los límites y condiciones de uso vigentes en su plataforma.

## Pasos

1. Entrá a [console.groq.com/keys](https://console.groq.com/keys).

2. Iniciá sesión o creá una cuenta en Groq.

3. Seleccioná **Create API Key**.

4. Definí el tiempo de caducidad de la clave.

5. Confirmá la creación y copiá el valor de **Secret Key**.

6. Abrí Alberdi Bot y pegá la clave en el campo **API key de Groq** de la barra lateral.

7. Ingresá al módulo **Chat** y realizá tu consulta.

> La secret key se muestra al crearla. Copiala antes de cerrar la ventana, ya que posiblemente no vuelva a estar disponible en texto plano.

## Uso local mediante `.env`

También podés configurar la clave en `constitucionbot/.env`:

```env
API_KEY_GROQ=tu_api_key_de_groq
MODEL_GROQ=openai/gpt-oss-20b
```

Luego ejecutá:

```bash
streamlit run app.py
```

## Seguridad

No compartas tu secret key ni la subas a GitHub. Si la clave se expone, revocala desde la consola de Groq y generá una nueva.
