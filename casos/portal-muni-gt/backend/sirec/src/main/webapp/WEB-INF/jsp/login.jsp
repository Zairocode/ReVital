<%@ page contentType="text/html; charset=UTF-8" %><%@ taglib prefix="s" uri="/struts-tags" %><!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>SIREC - Acceso de operadores</title></head>
<body style="font-family:sans-serif;max-width:420px;margin:40px auto">
<p style="background:#ffe066;padding:6px">SISTEMA DE DEMOSTRACION · Municipalidad ficticia</p>
<h1>SIREC · Acceso de operadores</h1>
<s:actionerror/>
<form action="entrar.action" method="post">
  <p><label>Usuario <input name="usuario" value="<s:property value="usuario"/>" autocomplete="username"></label></p>
  <p><label>Clave <input name="clave" type="password" autocomplete="current-password"></label></p>
  <p><button>Entrar</button></p>
</form></body></html>
